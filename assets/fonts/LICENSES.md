# Giấy phép font trong `assets/fonts/`

Cả 9 tệp font ở đây đều theo **SIL Open Font License, Version 1.1 (OFL-1.1)**. Thông tin dưới đây
đọc thẳng từ bảng `name` trong từng tệp font (name ID 0 = bản quyền, 5 = phiên bản, 8–12 = nhà phát hành/thiết
kế, 13 = mô tả giấy phép, 14 = URL giấy phép), không suy đoán. Toàn văn giấy phép ở cuối tệp này.

OFL cho dùng, nhúng, sửa và phân phối lại, kể cả thương mại, với các điều kiện chính: khi phân phối lại font thì
kèm thông báo bản quyền và toàn văn giấy phép (điều 2), không bán riêng font (điều 1), font phải giữ nguyên dưới OFL
(điều 5). Repo này chứa sẵn font nên chia sẻ repo (kể cả đẩy lên GitHub) là phân phối lại font: tệp này giữ thông
báo bản quyền và giấy phép đó. Điều 5 nói rõ yêu cầu giữ font dưới OFL *không áp cho tài liệu tạo bằng font* — ảnh và
thẻ do pipeline dựng ra không bị OFL ràng buộc.

**Nguồn tải.** Repo không ghi nơi đã tải từng font (commit thêm font: `1c932a3` ngày 20/08/2026 và `f5343a3` ngày
23/08/2026, cả hai không có URL). Dòng "Phát hành" dưới đây là nơi phát hành mà chính tệp font tự khai, không phải
nơi đã tải thật. Thêm font mới thì thêm mục ở đây (`tests/test_assets_licenses.py` bắt trường hợp quên); đọc
bảng `name` bằng fontTools: `TTFont(đường_dẫn)["name"].getName(ID, 3, 1, 0x409)`.

## Danh sách

### Be Vietnam Pro

- Tệp: `BeVietnamPro-Regular.ttf`, `BeVietnamPro-Bold.ttf`
- Bản quyền (name ID 0): Copyright 2021 The Be Vietnam Pro Project Authors (https://github.com/bettergui/BeVietnamPro)
- Phiên bản (ID 5): Version 1.002; ttfautohint (v1.8.3)
- Phát hành (ID 8–12): nhà phát hành Yellow Type Foundry; thiết kế Lam Bao, Tony Le, Vietanh Nguyen; web https://yellowtype.com/
- Giấy phép (ID 13): This Font Software is licensed under the SIL Open Font License, Version 1.1. This license is available with a FAQ at: https://scripts.sil.org/OFL
- URL giấy phép (ID 14): https://scripts.sil.org/OFL

### Inter

- Tệp: `Inter.ttf`
- Bản quyền (name ID 0): Copyright 2016 The Inter Project Authors (https://github.com/rsms/inter)
- Phiên bản (ID 5): Version 4.001;git-66647c0bb
- Phát hành (ID 8–12): nhà phát hành rsms; thiết kế Rasmus Andersson; web https://rsms.me/
- Nhãn hiệu (ID 7): Inter UI and Inter is a trademark of rsms.
- Giấy phép (ID 13): This Font Software is licensed under the SIL Open Font License, Version 1.1. This license is available with a FAQ at: https://openfontlicense.org
- URL giấy phép (ID 14): https://openfontlicense.org

### JetBrains Mono

- Tệp: `JetBrainsMono-Regular.ttf`, `JetBrainsMono-Bold.ttf`, `JetBrainsMono-ExtraBold.ttf`
- Bản quyền (name ID 0): Copyright 2020 The JetBrains Mono Project Authors (https://github.com/JetBrains/JetBrainsMono)
- Phiên bản (ID 5): Version 2.305; ttfautohint (v1.8.4.7-5d5b)
- Phát hành (ID 8–12): nhà phát hành JetBrains; thiết kế Philipp Nurullin, Konstantin Bulenkov; web https://www.jetbrains.com
- Nhãn hiệu (ID 7): JetBrains Mono is a trademark of JetBrains s.r.o.
- Giấy phép (ID 13): This Font Software is licensed under the SIL Open Font License, Version 1.1. This license is available with a FAQ at: https://openfontlicense.org
- URL giấy phép (ID 14): https://openfontlicense.org

### Noto Serif

- Tệp: `NotoSerif.ttf`
- Bản quyền (name ID 0): Copyright 2015 Google LLC. All Rights Reserved.
- Phiên bản (ID 5): Version 2.004; ttfautohint (v1.8.3) -l 8 -r 50 -G 200 -x 14 -D latn -f none -a qsq -X ""
- Phát hành (ID 8–12): nhà phát hành Monotype Imaging Inc.; thiết kế Monotype Design Team; web http://www.google.com/get/noto/, http://www.monotype.com/studio
- Nhãn hiệu (ID 7): Noto is a trademark of Google LLC.
- Giấy phép (ID 13): This Font Software is licensed under the SIL Open Font License, Version 1.1. This Font Software is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the SIL Open Font License for the specific language, permissions and limitations governing your use of this Font Software.
- URL giấy phép (ID 14): http://scripts.sil.org/OFL

### Noto Serif Display

- Tệp: `NotoSerifDisplay.ttf`
- Bản quyền (name ID 0): Copyright 2016 Google Inc. All Rights Reserved.
- Phiên bản (ID 5): Version 2.003; ttfautohint (v1.8.3) -l 8 -r 50 -G 200 -x 14 -D latn -f none -a qsq -X ""
- Phát hành (ID 8–12): nhà phát hành Monotype Imaging Inc.; thiết kế Monotype Design Team; web http://www.google.com/get/noto/, http://www.monotype.com/studio
- Nhãn hiệu (ID 7): Noto is a trademark of Google Inc.
- Giấy phép (ID 13): This Font Software is licensed under the SIL Open Font License, Version 1.1. This Font Software is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the SIL Open Font License for the specific language, permissions and limitations governing your use of this Font Software.
- URL giấy phép (ID 14): http://scripts.sil.org/OFL

### Oswald

- Tệp: `Oswald.ttf`
- Bản quyền (name ID 0): Copyright 2016 The Oswald Project Authors (https://github.com/googlefonts/OswaldFont)
- Phiên bản (ID 5): Version 4.103;gftools[0.9.33.dev8+g029e19f]
- Phát hành (ID 8–12): nhà phát hành Vernon Adams; thiết kế Vernon Adams; web http://www.sansoxygen.com
- Giấy phép (ID 13): This Font Software is licensed under the SIL Open Font License, Version 1.1. This license is available with a FAQ at: https://scripts.sil.org/OFL
- URL giấy phép (ID 14): https://scripts.sil.org/OFL

## Toàn văn SIL Open Font License, Version 1.1

Văn bản theo bản SPDX của OFL-1.1 (`spdx/license-list-data`, `text/OFL-1.1.txt`). Thông báo bản quyền riêng của
từng họ font nằm ở mục tương ứng phía trên.

```text
SIL OPEN FONT LICENSE

Version 1.1 - 26 February 2007

PREAMBLE

The goals of the Open Font License (OFL) are to stimulate worldwide development of collaborative font projects, to support the font creation efforts of academic and linguistic communities, and to provide a free and open framework in which fonts may be shared and improved in partnership with others.

The OFL allows the licensed fonts to be used, studied, modified and redistributed freely as long as they are not sold by themselves. The fonts, including any derivative works, can be bundled, embedded, redistributed and/or sold with any software provided that any reserved names are not used by derivative works. The fonts and derivatives, however, cannot be released under any other type of license. The requirement for fonts to remain under this license does not apply to any document created using the fonts or their derivatives.

DEFINITIONS

"Font Software" refers to the set of files released by the Copyright Holder(s) under this license and clearly marked as such. This may include source files, build scripts and documentation.

"Reserved Font Name" refers to any names specified as such after the copyright statement(s).

"Original Version" refers to the collection of Font Software components as distributed by the Copyright Holder(s).

"Modified Version" refers to any derivative made by adding to, deleting, or substituting — in part or in whole — any of the components of the Original Version, by changing formats or by porting the Font Software to a new environment.

"Author" refers to any designer, engineer, programmer, technical writer or other person who contributed to the Font Software.

PERMISSION & CONDITIONS

Permission is hereby granted, free of charge, to any person obtaining a copy of the Font Software, to use, study, copy, merge, embed, modify, redistribute, and sell modified and unmodified copies of the Font Software, subject to the following conditions:

1) Neither the Font Software nor any of its individual components, in Original or Modified Versions, may be sold by itself.

2) Original or Modified Versions of the Font Software may be bundled, redistributed and/or sold with any software, provided that each copy contains the above copyright notice and this license. These can be included either as stand-alone text files, human-readable headers or in the appropriate machine-readable metadata fields within text or binary files as long as those fields can be easily viewed by the user.

3) No Modified Version of the Font Software may use the Reserved Font Name(s) unless explicit written permission is granted by the corresponding Copyright Holder. This restriction only applies to the primary font name as presented to the users.

4) The name(s) of the Copyright Holder(s) or the Author(s) of the Font Software shall not be used to promote, endorse or advertise any Modified Version, except to acknowledge the contribution(s) of the Copyright Holder(s) and the Author(s) or with their explicit written permission.

5) The Font Software, modified or unmodified, in part or in whole, must be distributed entirely under this license, and must not be distributed under any other license. The requirement for fonts to remain under this license does not apply to any document created using the Font Software.

TERMINATION

This license becomes null and void if any of the above conditions are not met.

DISCLAIMER

THE FONT SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO ANY WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT OF COPYRIGHT, PATENT, TRADEMARK, OR OTHER RIGHT. IN NO EVENT SHALL THE COPYRIGHT HOLDER BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, INCLUDING ANY GENERAL, SPECIAL, INDIRECT, INCIDENTAL, OR CONSEQUENTIAL DAMAGES, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF THE USE OR INABILITY TO USE THE FONT SOFTWARE OR FROM OTHER DEALINGS IN THE FONT SOFTWARE.
```
