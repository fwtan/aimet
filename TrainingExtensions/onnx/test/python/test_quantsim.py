# /usr/bin/env python3.8
# -*- mode: python -*-
# =============================================================================
#  @@-COPYRIGHT-START-@@
#
#  Copyright (c) 2022-2023, Qualcomm Innovation Center, Inc. All rights reserved.
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
import json
import os
import torch
import numpy as np
from onnx import load_model
import onnxruntime as ort
import pytest
from aimet_common.defs import QuantScheme, QuantizationDataType
from aimet_common.quantsim_config.utils import get_path_for_per_channel_config
from aimet_onnx.quantsim import QuantizationSimModel, load_encodings_to_sim
from aimet_onnx.qc_quantize_op import OpMode
from aimet_onnx.utils import make_dummy_input
from models.models_for_tests import SingleResidual
from models.models_for_tests import build_dummy_model, single_residual_model, BNAfterConv


class DummyModel(SingleResidual):
    """
    Model
    """
    def __init__(self):
        super().__init__()
        # change padding size to 0, onnxruntime only support input size is the factor of output size for pooling
        self.conv4 = torch.nn.Conv2d(32, 8, kernel_size=2, stride=2, padding=0, bias=True)
        # TODO
        # remove bn layer for currently not supporting non-4 dim param tensors
        del self.bn1
        del self.bn2

    def forward(self, inputs):
        x = self.conv1(inputs)
        # TODO
        # remove bn layer for currently not supporting non-4 dim param tensors
        # x = self.bn1(x)
        x = self.relu1(x)
        x = self.maxpool(x)

        # Save the output of MaxPool as residual.
        residual = x

        x = self.conv2(x)
        # TODO
        # remove bn layer for currently not supporting non-4 dim param tensors
        # x = self.bn2(x)
        x = self.relu2(x)
        x = self.conv3(x)

        # Add the residual
        # AdaptiveAvgPool2d is used to get the desired dimension before adding.
        residual = self.conv4(residual)
        residual = self.ada(residual)
        x += residual
        x = self.relu3(x)

        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        x = self.fc(x)

        return x


class TestQuantSim:
    """Tests for QuantizationSimModel"""
    def test_insert_quantize_op_nodes(self):
        """ Test to insert qc quantize op to the graph"""
        model = build_dummy_model()
        dummy_input = make_dummy_input(model)
        sim = QuantizationSimModel(model, dummy_input)
        assert len(sim.model.nodes()) == 14

        node_ls = [node.op_type for node in sim.model.nodes()]
        assert node_ls == ['Conv', 'Relu', 'MaxPool', 'Flatten', 'Gemm'] + ['QcQuantizeOp'] * 9

        # Check if qc quantize op node is correctly connect to the corresponding onnx node
        assert sim.model.find_node_by_name('QcQuantizeOp_input', [], sim.model.graph()).output[0] == \
               sim.model.find_node_by_name('conv', [], sim.model.graph()).input[0]
        # Check if op_mode is set correctly for each qc quantize op node
        qc_quantize_op_dict = sim.get_qc_quantize_op()
        for name in sim.param_names:
            assert qc_quantize_op_dict[name].op_mode == OpMode.oneShotQuantizeDequantize
        for name in sim.activation_names:
            assert qc_quantize_op_dict[name].op_mode == OpMode.updateStats

    def test_create_quantsim_dynamic_batch_size(self):
        """ Test to insert qc quantize op to the graph"""
        model = BNAfterConv()
        inputs = torch.randn((2, 10, 24, 24))
        torch.onnx.export(model, inputs, '/tmp/dummy_model.onnx',
                          training=torch.onnx.TrainingMode.PRESERVE,
                          input_names=['input'], output_names=['output'],
                          dynamic_axes={
                              'input': {0: 'batch_size'},
                              'output': {0: 'batch_size'},
                          })

        onnx_model = load_model('/tmp/dummy_model.onnx')

        dummy_input = make_dummy_input(onnx_model)
        sim = QuantizationSimModel(onnx_model, dummy_input)
        sim.session.run(None, dummy_input)

    def test_compute_encodings(self):
        """Test to perform compute encodings"""
        model = build_dummy_model()
        sim = QuantizationSimModel(model)

        for quantizer in sim.qc_quantize_op_dict:
            sim.qc_quantize_op_dict[quantizer].enabled = True

        for name, qc_op in sim.get_qc_quantize_op().items():
            assert qc_op.quant_info.tensorQuantizerRef[0].isEncodingValid is False

        def callback(session, args):
            in_tensor = {'input': np.random.rand(1, 3, 32, 32).astype(np.float32)}
            session.run(None, in_tensor)

        sim.compute_encodings(callback, None)

        for name, qc_op in sim.get_qc_quantize_op().items():
            assert qc_op.encodings[0].bw == 8

        for name, qc_op in sim.get_qc_quantize_op().items():
            assert qc_op.quant_info.tensorQuantizerRef[0].isEncodingValid is True
            assert qc_op.op_mode == OpMode.quantizeDequantize

    def test_export_model_with_quant_args(self):
        """Test to export encodings and model"""
        if not os.path.exists('./tmp'):
            os.mkdir('./tmp')
        model = build_dummy_model()
        sim = QuantizationSimModel(model, default_activation_bw=16, default_param_bw=16,
                                   quant_scheme=QuantScheme.post_training_tf)

        for quantizer in sim.qc_quantize_op_dict:
            sim.qc_quantize_op_dict[quantizer].enabled = True


        def dummy_callback(session, args):
            pass

        sim.compute_encodings(dummy_callback, None)

        sim.export('./tmp/', 'quant_sim_model_with_quant_args')
        with open('./tmp/quant_sim_model_with_quant_args.encodings') as json_file:
            encoding_data = json.load(json_file)

        assert "quantizer_args" in encoding_data
        quantizer_args = encoding_data["quantizer_args"]
        assert quantizer_args["activation_bitwidth"] == 16
        assert quantizer_args["param_bitwidth"] == 16
        assert not quantizer_args["per_channel_quantization"]
        assert quantizer_args["quant_scheme"] == QuantScheme.post_training_tf.name
        assert quantizer_args["dtype"] == "int"
        assert "is_symmetric" in quantizer_args

    def test_export_model(self):
        """Test to export encodings and model"""
        if not os.path.exists('/tmp'):
            os.mkdir('/tmp')
        model = build_dummy_model()
        sim = QuantizationSimModel(model)

        for quantizer in sim.qc_quantize_op_dict:
            sim.qc_quantize_op_dict[quantizer].enabled = True

        def dummy_callback(session, args):
            pass

        sim.compute_encodings(dummy_callback, None)
        sim.export('/tmp/', 'quant_sim_model')

        with open('/tmp/quant_sim_model.encodings', 'rb') as json_file:
            encoding_data = json.load(json_file)
        activation_keys = list(encoding_data["activation_encodings"].keys())
        assert activation_keys == ['3', '4', '5', 'input', 'output']
        for act in activation_keys:
            act_encodings_keys = list(encoding_data["activation_encodings"][act][0].keys())
            assert act_encodings_keys == ['bitwidth', 'dtype', 'is_symmetric', 'max', 'min', 'offset', 'scale']

        param_keys = list(encoding_data['param_encodings'].keys())
        assert param_keys == ['conv_b', 'conv_w', 'fc_b', 'fc_w']
        for param in param_keys:
            param_encodings_keys = list(encoding_data["param_encodings"][param][0].keys())
            assert param_encodings_keys == ['bitwidth', 'dtype', 'is_symmetric', 'max', 'min', 'offset', 'scale']

    def test_single_residual(self):
        model = single_residual_model().model
        sim = QuantizationSimModel(model, use_cuda=False)
        for quantizer in sim.qc_quantize_op_dict:
            sim.qc_quantize_op_dict[quantizer].enabled = True

        def dummy_callback(session, args):
            pass

        sim.compute_encodings(dummy_callback, None)
        sim.export('/tmp/', 'quant_sim_model')

        with open('/tmp/quant_sim_model.encodings', 'rb') as json_file:
            encoding_data = json.load(json_file)
        activation_keys = list(encoding_data["activation_encodings"].keys())
        assert activation_keys == ['20', '21', '24', '25', '26', '28', '29', '30', '31', '33', '34', '44', '47', 'input', 'output']
        for act in activation_keys:
            act_encodings_keys = list(encoding_data["activation_encodings"][act][0].keys())
            assert act_encodings_keys == ['bitwidth', 'dtype', 'is_symmetric', 'max', 'min', 'offset', 'scale']

        param_keys = list(encoding_data['param_encodings'].keys())
        assert param_keys == ['45', '46', '48', '49', 'conv3.weight', 'conv4.bias', 'conv4.weight', 'fc.bias', 'fc.weight']
        for param in param_keys:
            param_encodings_keys = list(encoding_data["param_encodings"][param][0].keys())
            assert param_encodings_keys == ['bitwidth', 'dtype', 'is_symmetric', 'max', 'min', 'offset', 'scale']

    @pytest.mark.cuda
    def test_compare_encodings_cpu_gpu(self):
        """Test to compare encodings with PT"""
        if not os.path.exists('/tmp'):
            os.mkdir('/tmp')

        def onnx_callback(session, inputs):
            in_tensor = {'input': inputs}
            session.run(None, in_tensor)
        np.random.seed(0)
        torch.manual_seed(0)

        inputs = np.random.rand(128, 3, 32, 32).astype(np.float32)
        model = DummyModel()
        model.eval()

        torch.onnx.export(model, torch.as_tensor(inputs), '/tmp/dummy_model.onnx', training=torch.onnx.TrainingMode.PRESERVE,
                          input_names=['input'], output_names=['output'])

        onnx_model_cpu = load_model('/tmp/dummy_model.onnx')
        onnx_model_gpu = load_model('/tmp/dummy_model.onnx')

        onnx_sim_cpu = QuantizationSimModel(onnx_model_cpu, use_cuda=False, quant_scheme=QuantScheme.post_training_tf_enhanced)
        onnx_sim_gpu = QuantizationSimModel(onnx_model_gpu, use_cuda=True, quant_scheme=QuantScheme.post_training_tf_enhanced)

        for node in onnx_sim_gpu.model.graph().node:
            if node.op_type == "QcQuantizeOp":
                if 'CUDAExecutionProvider' in ort.get_available_providers():
                    assert node.domain == "aimet.customop.cuda"
        for node in onnx_sim_cpu.model.graph().node:
            if node.op_type == "QcQuantizeOp":
                assert node.domain == "aimet.customop.cpu"

        onnx_sim_cpu.compute_encodings(onnx_callback, inputs)
        onnx_sim_gpu.compute_encodings(onnx_callback, inputs)
        out_cpu = onnx_sim_cpu.session.run(None, {'input': inputs})[0]
        out_gpu = onnx_sim_gpu.session.run(None, {'input': inputs})[0]
        onnx_sim_cpu.export('/tmp', 'onnx_sim_cpu')
        onnx_sim_gpu.export('/tmp', 'onnx_sim_gpu')

        assert(np.max(np.abs(out_cpu - out_gpu)) < 0.05)
        print(np.max(np.abs(out_cpu - out_gpu)))

        with open('/tmp/onnx_sim_cpu.encodings') as f:
            cpu_encodings = json.load(f)
        with open('/tmp/onnx_sim_gpu.encodings') as f:
            gpu_encodings = json.load(f)

        for name in list(cpu_encodings['activation_encodings'].keys()):
            assert round(cpu_encodings['activation_encodings'][name][0]['max'], 4) == \
                   round(gpu_encodings['activation_encodings'][name][0]['max'], 4)
            assert round(cpu_encodings['activation_encodings'][name][0]['min'], 4) == \
                   round(gpu_encodings['activation_encodings'][name][0]['min'], 4)
            assert round(cpu_encodings['activation_encodings'][name][0]['scale'], 4) == \
                   round(gpu_encodings['activation_encodings'][name][0]['scale'], 4)
            assert cpu_encodings['activation_encodings'][name][0]['offset'] == \
                   gpu_encodings['activation_encodings'][name][0]['offset']

        for name in list(cpu_encodings['param_encodings'].keys()):
            assert round(cpu_encodings['param_encodings'][name][0]['max'], 4) == \
                   round(gpu_encodings['param_encodings'][name][0]['max'], 4)
            assert round(cpu_encodings['param_encodings'][name][0]['min'], 4) == \
                   round(gpu_encodings['param_encodings'][name][0]['min'], 4)
            assert round(cpu_encodings['param_encodings'][name][0]['scale'], 4) == \
                   round(gpu_encodings['param_encodings'][name][0]['scale'], 4)
            assert cpu_encodings['param_encodings'][name][0]['offset'] == \
                   gpu_encodings['param_encodings'][name][0]['offset']

    @pytest.mark.cuda
    def test_compare_encodings_cpu_gpu_fp16(self):
        """Test to compare encodings with PT"""
        if not os.path.exists('/tmp'):
            os.mkdir('/tmp')

        np.random.seed(0)
        torch.manual_seed(0)

        inputs = np.random.rand(128, 3, 32, 32).astype(np.float32)
        model = DummyModel()
        model.eval()

        torch.onnx.export(model, torch.as_tensor(inputs), '/tmp/dummy_model.onnx',
                          training=torch.onnx.TrainingMode.PRESERVE,
                          input_names=['input'], output_names=['output'])

        onnx_model_cpu = load_model('/tmp/dummy_model.onnx')
        onnx_model_gpu = load_model('/tmp/dummy_model.onnx')

        onnx_sim_cpu = QuantizationSimModel(onnx_model_cpu, use_cuda=False,
                                            quant_scheme=QuantScheme.post_training_tf_enhanced,
                                            default_data_type=QuantizationDataType.float, default_param_bw=16,
                                            default_activation_bw=16)
        onnx_sim_gpu = QuantizationSimModel(onnx_model_gpu, use_cuda=True,
                                            quant_scheme=QuantScheme.post_training_tf_enhanced,
                                            default_data_type=QuantizationDataType.float, default_param_bw=16,
                                            default_activation_bw=16)

        for node in onnx_sim_gpu.model.graph().node:
            if node.op_type == "QcQuantizeOp":
                if 'CUDAExecutionProvider' in ort.get_available_providers():
                    assert node.domain == "aimet.customop.cuda"
        for node in onnx_sim_cpu.model.graph().node:
            if node.op_type == "QcQuantizeOp":
                assert node.domain == "aimet.customop.cpu"

        out_cpu = onnx_sim_cpu.session.run(None, {'input': inputs})[0]
        out_gpu = onnx_sim_gpu.session.run(None, {'input': inputs})[0]

        assert (np.max(np.abs(out_cpu - out_gpu)) < 0.05)

    def test_per_channel_quantization(self):
        model = single_residual_model().model
        sim = QuantizationSimModel(model, use_cuda=False, config_file=get_path_for_per_channel_config())
        def dummy_callback(session, args):
            in_tensor = {'input': np.random.rand(1, 3, 32, 32).astype(np.float32)}
            session.run(None, in_tensor)
        sim.qc_quantize_op_dict['fc.weight'].enable_per_channel_quantization()
        sim.compute_encodings(dummy_callback, None)

        sim.export('./tmp/', 'encodings')
        with open('./tmp/encodings.encodings') as json_file:
            encoding_data = json.load(json_file)

        for param_name in sim.param_names:
            qc_op = sim.qc_quantize_op_dict[param_name]
            if qc_op.quant_info.usePerChannelMode and qc_op.enabled:
                num_channels = qc_op.tensor_quantizer_params.num_output_channels
                assert num_channels == len(qc_op.encodings)
                assert num_channels == len(encoding_data['param_encodings'][param_name])
                for encoding in qc_op.encodings:
                    assert encoding.bw == 8
                    assert encoding.min != encoding.max


    def test_load_encodings_ptq(self):
        model = single_residual_model().model
        sim = QuantizationSimModel(model)

        def callback(session, args):
            in_tensor = {'input': np.random.rand(1, 3, 32, 32).astype(np.float32)}
            session.run(None, in_tensor)

        dummy_tensor = {'input': np.random.rand(1, 3, 32, 32).astype(np.float32)}

        sim.compute_encodings(callback, None)
        sim.export('/tmp', 'onnx_sim')

        out2 = sim.session.run(None, dummy_tensor)

        del sim

        sim = QuantizationSimModel(model)
        load_encodings_to_sim(sim, '/tmp/onnx_sim.encodings')
        out3 = sim.session.run(None, dummy_tensor)

        assert np.allclose(out2, out3)

    def test_load_encodings_pcq(self):
        model = single_residual_model().model
        sim = QuantizationSimModel(model, config_file=get_path_for_per_channel_config())

        def callback(session, args):
            in_tensor = {'input': np.random.rand(1, 3, 32, 32).astype(np.float32)}
            session.run(None, in_tensor)

        dummy_tensor = {'input': np.random.rand(1, 3, 32, 32).astype(np.float32)}

        sim.compute_encodings(callback, None)
        sim.export('/tmp', 'onnx_sim')

        out2 = sim.session.run(None, dummy_tensor)

        del sim

        sim = QuantizationSimModel(model, config_file=get_path_for_per_channel_config())
        load_encodings_to_sim(sim, '/tmp/onnx_sim.encodings')
        out3 = sim.session.run(None, dummy_tensor)

        assert np.allclose(out2, out3)
