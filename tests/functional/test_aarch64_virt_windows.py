#!/usr/bin/env python3
#
# Functional test that boots Windows Validation OS.
# https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/validation-os-overview
#
# Copyright (c) 2024 Linaro Ltd.
#
# Author:
#  Pierrick Bouvier <pierrick.bouvier@linaro.org>
#
# SPDX-License-Identifier: GPL-2.0-or-later

import logging
import os
import shutil
import time

from qemu_test import BUILD_DIR
from qemu_test import QemuSystemTest, Asset
from qemu_test.tesseract import tesseract_ocr
from unittest import skipUnless


class Aarch64VirtWindowsMachine(QemuSystemTest):
    # VM image comes from iso download at:
    # https://aka.ms/DownloadValidationOS_arm64
    ASSET_WINVOS_IMG = Asset(
        ('https://fileserver.linaro.org/s/iTFEgXfpa9FfrGk/'
         'download/ValidationOS.vhdx'),
         'ae6d95d6657a2d644ecff42abd713b11c808756416ee610a1fcf86cb34d49675')

    def test_win_virt_tcg(self):
        self.set_machine('virt')
        self.require_accelerator('tcg')

        orig_img_path = self.ASSET_WINVOS_IMG.fetch()
        img_path = os.path.join(self.workdir, 'winvos.vhdx')
        shutil.copy(orig_img_path, img_path)
        os.chmod(img_path, 0o644)

        self.vm.add_args('-accel', 'tcg')
        self.vm.add_args('-cpu', 'max,pauth-impdef=on')
        self.vm.add_args('-machine',
                         'virt,its=on,'
                         'virtualization=false,'
                         'gic-version=3')
        self.vm.add_args('-smp', '1', '-m', '1024')
        self.vm.add_args('-bios', os.path.join(BUILD_DIR, 'pc-bios',
                                               'edk2-aarch64-code.fd'))
        self.vm.add_args('-device', 'ramfb')
        self.vm.add_args('-device', 'nvme,drive=hd0,serial=00000001')
        self.vm.add_args('-drive', f'if=none,media=disk,id=hd0,file={img_path}')

        self.vm.launch()

        screenshot_path = os.path.join(self.workdir, "dump_winvos.ppm")
        # We now capture screen and use tesseract to perform OCR.
        # Windows boot is silent, until a terminal and a prompt appear.
        # To debug this test, launch the test, and display captured screen with:
        # feh $(find | grep dump_winvos.ppm)
        while True:
            time.sleep(1)
            self.vm.cmd('human-monitor-command',
                        command_line='screendump %s' % screenshot_path)
            lines = tesseract_ocr(screenshot_path)
            # wait for prompt to appear 'C:\windows\system32>'
            # tesseract can't recognize 'C' because character is mixed with
            # border of window.
            if 'windows\system32>' in ''.join(lines).lower():
                break


if __name__ == '__main__':
    QemuSystemTest.main()
