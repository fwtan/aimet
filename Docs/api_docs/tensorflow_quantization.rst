==================================
AIMET TensorFlow Quantization APIs
==================================

AIMET Quantization for TensorFlow provides the following functionality
   - :ref:`Quantization Simulation<api-tf-quantsim>`: Allows ability to simulate inference and training on quantized hardware
   - :ref:`QuantAnalyzer<api-tensorflow-quant-analyzer>`: Analyzes the model and points out sensitive ops to quantization
   - :ref:`Adaptive Rounding<api-tf-adaround>`: Post-training quantization technique to optimize rounding of weight tensors
   - :ref:`Cross-Layer Equalization<api-tf-cle>`: Post-training quantization technique to equalize layer parameters
   - :ref:`Bias Correction<api-tf-bias-correction>`: Post-training quantization technique to correct shift in layer outputs due to quantization noise
   - :ref:`AutoQuant API<api-tf-auto-quant>`: Unified API that integrates the post-training quantization techniques provided by AIMET
   - :ref:`BN Re-estimation APIs<api-tensorflow-bn-reestimation>`: APIs that Re-estimate BN layers' statistics and fold the BN layers

