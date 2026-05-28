"""
生成应用图标。运行一次即可：python create_icon.py
"""
import struct
import zlib
import os


def create_icon():
    """生成一个百度网盘蓝色风格的 256x256 ICO 图标。"""
    size = 256

    # 创建 RGBA 像素数据（蓝色云朵风格简化图标）
    pixels = bytearray()

    # 简化的云盘图标：蓝色圆角矩形背景 + 白色云朵形状
    for y in range(size):
        for x in range(size):
            # 归一化坐标
            nx = x / size
            ny = y / size

            # 蓝色圆角矩形背景
            margin = 0.08
            corner_r = 0.15
            in_rect = False
            if (margin + corner_r <= nx <= 1 - margin - corner_r and
                    margin <= ny <= 1 - margin):
                in_rect = True
            elif (margin <= nx <= 1 - margin and
                  margin + corner_r <= ny <= 1 - margin - corner_r):
                in_rect = True
            else:
                # 检查四个角
                corners = [
                    (margin + corner_r, margin + corner_r),
                    (1 - margin - corner_r, margin + corner_r),
                    (margin + corner_r, 1 - margin - corner_r),
                    (1 - margin - corner_r, 1 - margin - corner_r),
                ]
                for cx, cy in corners:
                    if (nx - cx) ** 2 + (ny - cy) ** 2 <= corner_r ** 2:
                        # 检查是否在矩形范围内
                        if (margin <= nx <= 1 - margin and margin <= ny <= 1 - margin):
                            in_rect = True
                            break

            if in_rect:
                # 白色云朵形状（简化）
                cloud_cx, cloud_cy = 0.5, 0.45
                cloud_r = 0.22
                # 主圆
                in_cloud = (nx - cloud_cx) ** 2 + (ny - cloud_cy) ** 2 < cloud_r ** 2
                # 左侧小圆
                in_cloud = in_cloud or (nx - 0.35) ** 2 + (ny - 0.5) ** 2 < 0.12 ** 2
                # 右侧小圆
                in_cloud = in_cloud or (nx - 0.65) ** 2 + (ny - 0.5) ** 2 < 0.12 ** 2
                # 底部矩形
                in_cloud = in_cloud or (0.3 <= nx <= 0.7 and 0.4 <= ny <= 0.62)

                # 上箭头（上传标识）
                in_arrow = False
                arrow_cx = 0.5
                if 0.46 <= nx <= 0.54 and 0.25 <= ny <= 0.42:
                    in_arrow = True
                # 箭头头部
                if 0.38 <= nx <= 0.62 and 0.2 <= ny <= 0.3:
                    if abs(nx - 0.5) <= (0.3 - ny) * 0.8:
                        in_arrow = True

                if in_cloud or in_arrow:
                    r, g, b, a = 255, 255, 255, 255
                else:
                    r, g, b, a = 43, 124, 233, 255  # #2B7CE9
            else:
                r, g, b, a = 0, 0, 0, 0  # 透明

            pixels.extend([b, g, r, a])  # ICO 格式是 BGRA

    # 编码为 PNG
    png_data = _encode_png(size, size, bytes(pixels))

    # 写入 ICO 文件
    ico_header = struct.pack("<HHH", 0, 1, 1)  # reserved, type=ico, count=1
    ico_entry = struct.pack("<BBBBHHII",
                            size if size < 256 else 0,
                            size if size < 256 else 0,
                            0, 0, 1, 32,
                            len(png_data), 22)
    ico_data = ico_header + ico_entry + png_data

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "icon.ico")
    with open(out_path, "wb") as f:
        f.write(ico_data)
    print(f"图标已生成：{out_path}")


def _encode_png(width, height, rgba_data):
    """简单的 PNG 编码器。"""
    def _chunk(chunk_type, data):
        c = chunk_type + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    header = b"\x89PNG\r\n\x1a\n"
    ihdr = _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))

    # 构建 IDAT 数据
    raw = bytearray()
    stride = width * 4
    for y in range(height):
        raw.append(0)  # filter none
        raw.extend(rgba_data[y * stride: (y + 1) * stride])
    idat = _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    iend = _chunk(b"IEND", b"")

    return header + ihdr + idat + iend


if __name__ == "__main__":
    create_icon()