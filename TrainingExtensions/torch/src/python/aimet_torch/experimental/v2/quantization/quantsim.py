# -*- mode: python -*-
# =============================================================================
#  @@-COPYRIGHT-START-@@
#
#  Copyright (c) 2024, Qualcomm Innovation Center, Inc. All rights reserved.
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions are met:
#
#  1. Redistributions of source code must retain the above copyright notice,
#     this list of conditions and the following disclaimer.
#
#  2. Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions and the following disclaimer in the documentation
#     and/or other materials provided with the distribution.
#
#  3. Neither the name of the copyright holder nor the names of its contributors
#     may be used to endorse or promote products derived from this software
#     without specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
#  AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
#  IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
#  ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
#  LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
#  CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
#  SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
#  INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
#  CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
#  ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
#  POSSIBILITY OF SUCH DAMAGE.
#
#  SPDX-License-Identifier: BSD-3-Clause
#
#  @@-COPYRIGHT-END-@@
# =============================================================================
""" Top level API for performing quantization simulation of a pytorch model """

import itertools

import torch

from aimet_torch.quantsim import QuantizationSimModel as V1QuantizationSimModel
import aimet_torch.quantsim as quantsim_v1
from aimet_torch.experimental.v2 import nn as aimet_nn
from aimet_torch.experimental.v2.nn.fake_quant import FakeQuantizationMixin
from aimet_torch.experimental.v2.nn.quant_base import BaseQuantizationMixin
from aimet_torch.experimental.v2.quantization.wrappers.builder import LazyQuantizeWrapper
from aimet_torch.experimental.v2.utils import patch_attr
from aimet_torch import utils


qc_quantize_modules_dict = {
    torch.nn.RNN: LazyQuantizeWrapper,
    torch.nn.LSTM: LazyQuantizeWrapper,
    torch.nn.GRU: LazyQuantizeWrapper,
}


class QuantizationSimModel(V1QuantizationSimModel):
    """
    Overriden QuantizationSimModel that does off-target quantization simulation using v2 quantsim blocks.
    """
    def __init__(self, *args, **kwargs): # pylint: disable=arguments-differ
        super().__init__(*args, **kwargs)

        # Quantization parameters are placed on cpu by default.
        # Move them to cuda device as necessary

        default_device = torch.device('cpu')

        for param_or_buffer in itertools.chain(self.model.parameters(), self.model.buffers()):
            if param_or_buffer.device.type != 'cpu':
                # Use the first non-cpu device as default device.
                # Default device is necessary for the input/output quantizers of
                # modules without any parameters such as ReLU
                default_device = param_or_buffer.device
                break

        for module in self.model.modules():
            if not isinstance(module, BaseQuantizationMixin):
                continue

            try:
                # Find the device of the first parameter of the orignal module
                param_or_buffer = next(iter(itertools.chain(module.parameters(recurse=False),
                                                            module.buffers(recurse=False))))
                device = param_or_buffer.device
            except StopIteration:
                # If the original module has no parameter, use default device
                device = default_device

            # Set quantization parameters to the device of the original module
            module.to(device=device)

    @staticmethod
    def _realize_quant_wrapper(module: LazyQuantizeWrapper) -> FakeQuantizationMixin:
        """
        Make wrapper builder into v2 quant wrapper

        :param module: wrapper builder to realize
        :return: realized v2 quant wrapper
        """
        return module.realize_v2_wrapper()

    def compute_encodings(self, forward_pass_callback, forward_pass_callback_args):
        """
        Computes encodings for all quantization sim nodes in the model. It is also used to find initial encodings for
        Range Learning

        :param forward_pass_callback: A callback function that simply runs forward passes on the model. This callback
            function should use representative data for the forward pass, so the calculated encodings work for all
            data samples. This callback internally chooses the number of data samples it wants to use for calculating
            encodings.
        :param forward_pass_callback_args: These argument(s) are passed to the forward_pass_callback as-is. Up to
            the user to determine the type of this parameter. E.g. could be simply an integer representing the number
            of data samples to use. Or could be a tuple of parameters or an object representing something more complex.
            If set to None, forward_pass_callback will be invoked with no parameters.
        :return: None

        """
        # Run forward iterations so we can collect statistics to compute the appropriate encodings
        with utils.in_eval_mode(self.model), torch.no_grad():
            with aimet_nn.compute_encodings(self.model):
                _ = forward_pass_callback(self.model, forward_pass_callback_args)

    def _create_quantizer_module(self, *args, **kwargs): # pylint: disable=arguments-differ
        # RNN, LSTM, and GRU don't require special handling in aimet V2
        with patch_attr(quantsim_v1, 'qc_quantize_modules_dict', qc_quantize_modules_dict):
            return super()._create_quantizer_module(*args, **kwargs)
