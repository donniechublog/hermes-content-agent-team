# assets/

Tệp nhị phân nằm thẳng trong git để máy nào sao chép repo về cũng chạy được, không có bước tải nào (xem `setup.sh`,
`check_env.py`). Repo được chia sẻ ra ngoài (GitHub) nên mỗi tệp ở đây phải có nguồn và giấy phép ghi rõ.

| Tệp | Dùng ở đâu | Giấy phép |
|---|---|---|
| `fonts/*.ttf` (9 tệp) | dựng ảnh và thẻ: `card.py`, `carousel.py`, `deck.py`, `render_edu.py`, `about_text.py`… | SIL OFL 1.1 — bản quyền từng họ font và toàn văn ở [`fonts/LICENSES.md`](fonts/LICENSES.md) |
| `face_detection_yunet_2023mar.onnx` | cổng chặn mặt người: `image_rules_{dre,ethan,kite}._load_yunet` (OpenCV `FaceDetectorYN`); `check_env.py` kiểm có mặt | MIT — mục dưới |

## face_detection_yunet_2023mar.onnx

- **Nguồn:** mô hình YuNet (Shiqi Yu và cộng sự), bản đóng gói trong OpenCV Zoo:
  <https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet>. README của thư mục đó dẫn về
  <https://github.com/ShiqiYu/libfacedetection.train> (mã huấn luyện) và ghi: "All files in this directory are
  licensed under MIT License".
- **Giấy phép:** MIT, `Copyright (c) 2020 Shiqi Yu <shiqi.yu@gmail.com>` (toàn văn bên dưới).
- **Đối chiếu (20/09/2026):** sha256 `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4`, 232589 byte — trùng với con trỏ Git LFS của tệp cùng tên ở nhánh `main`
  của `opencv/opencv_zoo` (`oid sha256:` và `size` giống hệt). Tức tệp này là đúng tệp OpenCV Zoo phát hành.
- **Nơi đã tải thật:** repo không ghi. Commit thêm tệp (`5467273`, 01/09/2026) chỉ ghi "model YuNet ~230KB", không có URL.
  Nguồn ở trên được xác lập bằng mã băm chứ không phải từ hồ sơ tải. Đổi tệp mô hình thì cập nhật mã băm ở đây
  (`tests/test_assets_licenses.py` so mã băm).
- **Trích dẫn** (theo README của OpenCV Zoo): Wu, Peng, Yu, "YuNet: A tiny millisecond-level face detector",
  *Machine Intelligence Research* 20(5), 2023, tr. 656–665.

### Toàn văn giấy phép MIT của YuNet

Nguyên văn tệp `LICENSE` cùng thư mục trong OpenCV Zoo. MIT yêu cầu giữ thông báo này trong mọi bản sao.

```text
MIT License

Copyright (c) 2020 Shiqi Yu <shiqi.yu@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
