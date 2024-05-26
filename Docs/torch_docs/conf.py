# -*- coding: utf-8 -*-
# pylint: skip-file
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
""" Configuration file for the Sphinx documentation builder """

import os
import sys


cur_dir = os.getcwd()
source_dir = os.path.join(cur_dir, '..')
sys.path.append(os.path.join(cur_dir, '..'))

# First import all universal settings from the base Docs/conf.py file
from conf import *

# Overwrite the master document and exclude irrelevant files from the build
master_doc = 'torch_docs/index'

# These paths are relative to the source directory
exclude_patterns = ["keras_code_examples*", "onnx_code_examples*", "tf_code_examples*", "torch_code_examples*",
                    "api_docs*", "Examples*", "user_guide/examples.rst"]

# These paths are relative to the current directory
html_static_path = [os.path.join(source_dir, "_static")]
templates_path = [os.path.join(source_dir, "_templates")]
html_logo = '../images/brain_logo.png'

# Version here refers to the AIMET torch v1/v2 version, not the AIMET release number
html_context["current_version"] = "PyTorch"


autosummary_filename_map = {
    "aimet_torch.v2.quantization.affine.quantize": "aimet_torch.v2.quantization.affine.quantize_"
}
