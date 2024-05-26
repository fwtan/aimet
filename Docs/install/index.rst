.. # =============================================================================
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

.. _ug-installation:

###################
AIMET Installation
###################

Quick Install
~~~~~~~~~~~~~

The AIMET PyTorch GPU PyPI packages are available for environments that meet the following requirements:

* 64-bit Intel x86-compatible processor
* Linux Ubuntu 22.04 LTS [Python 3.10] or Linux Ubuntu 20.04 LTS [Python 3.8]
* Torch 1.13+cu117

**Pip install:**

.. code-block::

    apt-get install liblapacke
    python3 -m pip install aimet-torch


Release Packages
~~~~~~~~~~~~~~~~

For other aimet variants, install the latest version from the .whl files hosted at https://github.com/quic/aimet/releases

**PyTorch**

.. parsed-literal::

    # Pytorch 1.13 with CUDA 11.x
    python3 -m pip install |download_url|\ |version|/aimet_torch-torch_gpu\_\ |version|\ |whl_suffix|
    # Pytorch 1.13 CPU only
    python3 -m pip install |download_url|\ |version|/aimet_torch-torch_cpu\_\ |version|\ |whl_suffix|


**TensorFlow**

.. parsed-literal::

    # Tensorflow 2.10 GPU with CUDA 11.x
    python3 -m pip install |download_url|\ |version|/aimet_tensorflow-tf_gpu\_\ |version|\ |whl_suffix|
    # Tensorflow 2.10 CPU only
    python3 -m pip install |download_url|\ |version|/aimet_tensorflow-tf_cpu\_\ |version|\ |whl_suffix|


**Onnx**

.. parsed-literal::

    # ONNX 1.14 GPU
    python3 -m pip install |download_url|\ |version|/aimet_onnx-onnx_gpu\_\ |version|\ |whl_suffix|
    # ONNX 1.14 CPU
    python3 -m pip install |download_url|\ |version|/aimet_onnx-onnx_cpu\_\ |version|\ |whl_suffix|

For previous AIMET releases, browse packages at https://github.com/quic/aimet/releases. Each release includes multiple python packages of the following format:

.. parsed-literal::

    # VARIANT in {torch_gpu, torch_cpu, tf_gpu, tf_cpu, onnx_gpu, onnx_cpu}
    # PACKAGE_PREFIX in {aimet_torch, aimet_tensorflow, aimet_onnx}
    <PACKAGE_PREFIX>-<VARIANT>_<VERSION>\ |whl_suffix|


.. |version| replace:: 1.31.0
.. |whl_suffix| replace:: -cp38-cp38-linux_x86_64.whl
.. |download_url| replace:: \https://github.com/quic/aimet/releases/download/

System Requirements
~~~~~~~~~~~~~~~~~~~

The AIMET package requires the following host platform setup:

* 64-bit Intel x86-compatible processor
* Linux Ubuntu: 22.04 LTS
* bash command shell
* For GPU variants:
    * Nvidia GPU card (Compute capability 5.2 or later)
    * nvidia-docker - Installation instructions: https://github.com/NVIDIA/nvidia-docker

To use the GPU accelerated training modules an Nvidia CUDA enabled GPU with a minimum Nvidia driver version of 455+ is required. Using the latest driver is always recommended, especially if using a newer GPU. Both CUDA and cuDNN (the more advanced CUDA interface) enabled GPUs are supported.


Advanced Installation Instructions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There are two ways to setup and install AIMET:
    * On your host machine
    * Using our pre-built development `Docker images <https://artifacts.codelinaro.org/ui/native/codelinaro-aimet/aimet-dev>`_

Please click on the appropriate link for installation instructions:

.. toctree::
   :titlesonly:
   :maxdepth: 3

   Install in Host Machine <install_host>
   Install in Docker Container <install_docker>
