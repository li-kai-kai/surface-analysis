import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams

# 设置中文字体支持
rcParams["font.sans-serif"] = ["Arial Unicode MS", "SimHei", "sans-serif"]
rcParams["axes.unicode_minus"] = False


def remove_tilt(x, y, z):
    """拟合平面 z = ax + by + c 并返回残差"""
    A = np.c_[x, y, np.ones(len(x))]
    coeff, _, _, _ = np.linalg.lstsq(A, z, rcond=None)
    a, b, c = coeff
    z_fit = a * x + b * y + c
    return z - z_fit


def calculate_surface_form(x, y, z):
    """去除一阶面形并计算PV值"""
    z_resid = remove_tilt(x, y, z)
    pv = np.max(z_resid) - np.min(z_resid)
    return z_resid, pv


def calculate_dynamic_sfma(
    x,
    y,
    z,
    slit_w=0.026,
    slit_h=0.008,
    slit_step_x=0.013,
    slit_step_y=0.001,
):
    """
    动态移动狭缝模拟 (SFMA)
    蛇形移动:从左下角开始,向上移动,然后向右移动一列,再向下移动,如此往复
    每次移除局部倾斜,累积残差并计算均值

    参数:
        x, y, z: 数据点坐标和高度值
        slit_w, slit_h: 狭缝的宽度和高度,单位米
        slit_step_x: slit在X方向的移动步长,单位米 (默认: 0.026m = 26mm)
        slit_step_y: slit在Y方向的移动步长,单位米 (默认: 0.0001m = 1mm)
    """

    min_x, max_x = np.min(x), np.max(x)
    min_y, max_y = np.min(y), np.max(y)

    x_sorted = np.sort(np.unique(x))
    y_sorted = np.sort(np.unique(y))
    step_x = np.median(np.diff(x_sorted)) if len(x_sorted) > 1 else (max_x - min_x)
    step_y = np.median(np.diff(y_sorted)) if len(y_sorted) > 1 else (max_y - min_y)

    n_cols = int(round((max_x - min_x) / step_x)) + 1
    n_rows = int(round((max_y - min_y) / step_y)) + 1

    col_indices = np.round((x - min_x) / step_x).astype(int)
    row_indices = np.round((y - min_y) / step_y).astype(int)

    grid_z = np.full((n_rows, n_cols), np.nan)
    grid_z[row_indices, col_indices] = z

    grid_x = min_x + np.arange(n_cols) * step_x
    grid_y = min_y + np.arange(n_rows) * step_y
    GX, GY = np.meshgrid(grid_x, grid_y)

    slit_px_w = int(round(slit_w / step_x))
    slit_px_h = int(round(slit_h / step_y))
    slit_step_px_x = int(round(slit_step_x / step_x))  # X方向移动步长(像素)
    slit_step_px_y = int(round(slit_step_y / step_y))  # Y方向移动步长(像素)

    # 使用均值累积
    layout_sum = np.zeros((n_rows, n_cols))
    layout_count = np.zeros((n_rows, n_cols))

    # 蛇形移动: 使用物理距离步长(转换为像素)
    for col_idx, col_start_idx in enumerate(range(-slit_px_w, n_cols, slit_step_px_x)):
        col_end_idx = col_start_idx + slit_px_w
        valid_start = max(0, col_start_idx)
        valid_end = min(n_cols, col_end_idx)

        if valid_start >= valid_end:
            continue

        col_z = grid_z[:, valid_start:valid_end]
        col_x = GX[:, valid_start:valid_end]
        col_y = GY[:, valid_start:valid_end]

        # 偶数列向上(从0开始),奇数列向下(从最大开始)
        if col_idx % 2 == 0:
            y_range = range(0, n_rows - slit_px_h + 1, slit_step_px_y)
        else:
            y_range = range(n_rows - slit_px_h, -1, -slit_step_px_y)

        for y_start_idx in y_range:
            y_end_idx = y_start_idx + slit_px_h

            win_z = col_z[y_start_idx:y_end_idx, :]
            win_x = col_x[y_start_idx:y_end_idx, :]
            win_y = col_y[y_start_idx:y_end_idx, :]

            mask = ~np.isnan(win_z)
            if np.sum(mask) < 10:
                continue

            z_f = win_z[mask]
            x_f = win_x[mask]
            y_f = win_y[mask]

            A = np.c_[x_f, y_f, np.ones(len(x_f))]
            coeff, _, _, _ = np.linalg.lstsq(A, z_f, rcond=None)
            a, b, c = coeff

            z_fit = a * win_x + b * win_y + c
            residual = win_z - z_fit

            valid_res_mask = ~np.isnan(residual)
            acc_sum_slice = layout_sum[y_start_idx:y_end_idx, valid_start:valid_end]
            acc_count_slice = layout_count[y_start_idx:y_end_idx, valid_start:valid_end]

            # 累积求和和计数
            acc_sum_slice[valid_res_mask] += residual[valid_res_mask]
            acc_count_slice[valid_res_mask] += 1

    # 计算均值
    with np.errstate(divide="ignore", invalid="ignore"):
        result_map = layout_sum / layout_count

    z_dynamic = result_map[row_indices, col_indices]
    return z_dynamic


def calculate_local_tilt(x, y, z):
    """
    计算局部倾斜角度 (梯度幅值)
    使用中心差分法计算X和Y方向斜率,边缘使用前向/后向差分,角点使用局部平面拟合
    """

    min_x, max_x = np.min(x), np.max(x)
    min_y, max_y = np.min(y), np.max(y)

    x_sorted = np.sort(np.unique(x))
    y_sorted = np.sort(np.unique(y))
    step_x = np.median(np.diff(x_sorted)) if len(x_sorted) > 1 else (max_x - min_x)
    step_y = np.median(np.diff(y_sorted)) if len(y_sorted) > 1 else (max_y - min_y)

    n_cols = int(round((max_x - min_x) / step_x)) + 1
    n_rows = int(round((max_y - min_y) / step_y)) + 1

    grid_z = np.full((n_rows, n_cols), np.nan)
    col_indices = np.round((x - min_x) / step_x).astype(int)
    row_indices = np.round((y - min_y) / step_y).astype(int)

    col_indices = np.clip(col_indices, 0, n_cols - 1)
    row_indices = np.clip(row_indices, 0, n_rows - 1)

    grid_z[row_indices, col_indices] = z

    slope_x = np.full((n_rows, n_cols), np.nan)
    slope_y = np.full((n_rows, n_cols), np.nan)

    def fit_local_plane(i, j, grid_z, step_x, step_y):
        """拟合3x3邻域的平面并返回斜率"""
        points_x, points_y, points_z = [], [], []

        for di in [-1, 0, 1]:
            for dj in [-1, 0, 1]:
                ni, nj = i + di, j + dj
                if 0 <= ni < grid_z.shape[0] and 0 <= nj < grid_z.shape[1]:
                    if not np.isnan(grid_z[ni, nj]):
                        points_x.append(nj * step_x)
                        points_y.append(ni * step_y)
                        points_z.append(grid_z[ni, nj])

        if len(points_z) >= 3:
            A = np.c_[points_x, points_y, np.ones(len(points_z))]
            try:
                coeff, _, _, _ = np.linalg.lstsq(A, points_z, rcond=None)
                return coeff[0], coeff[1]
            except:
                return np.nan, np.nan
        return np.nan, np.nan

    for i in range(n_rows):
        for j in range(n_cols):
            if np.isnan(grid_z[i, j]):
                continue

            is_left_edge = j == 0
            is_right_edge = j == n_cols - 1
            is_top_edge = i == 0
            is_bottom_edge = i == n_rows - 1

            is_corner = (is_left_edge or is_right_edge) and (
                is_top_edge or is_bottom_edge
            )
            is_edge = (
                is_left_edge or is_right_edge or is_top_edge or is_bottom_edge
            ) and not is_corner

            if is_corner:
                sx, sy = fit_local_plane(i, j, grid_z, step_x, step_y)
                slope_x[i, j] = sx
                slope_y[i, j] = sy
            elif is_edge:
                if is_left_edge:
                    if not np.isnan(grid_z[i, j + 1]):
                        slope_x[i, j] = (grid_z[i, j + 1] - grid_z[i, j]) / step_x
                elif is_right_edge:
                    if not np.isnan(grid_z[i, j - 1]):
                        slope_x[i, j] = (grid_z[i, j] - grid_z[i, j - 1]) / step_x
                else:
                    if not np.isnan(grid_z[i, j + 1]) and not np.isnan(
                        grid_z[i, j - 1]
                    ):
                        slope_x[i, j] = (grid_z[i, j + 1] - grid_z[i, j - 1]) / (
                            2 * step_x
                        )

                if is_top_edge:
                    if not np.isnan(grid_z[i + 1, j]):
                        slope_y[i, j] = (grid_z[i + 1, j] - grid_z[i, j]) / step_y
                elif is_bottom_edge:
                    if not np.isnan(grid_z[i - 1, j]):
                        slope_y[i, j] = (grid_z[i, j] - grid_z[i - 1, j]) / step_y
                else:
                    if not np.isnan(grid_z[i + 1, j]) and not np.isnan(
                        grid_z[i - 1, j]
                    ):
                        slope_y[i, j] = (grid_z[i + 1, j] - grid_z[i - 1, j]) / (
                            2 * step_y
                        )
            else:
                if not np.isnan(grid_z[i, j + 1]) and not np.isnan(grid_z[i, j - 1]):
                    slope_x[i, j] = (grid_z[i, j + 1] - grid_z[i, j - 1]) / (2 * step_x)
                if not np.isnan(grid_z[i + 1, j]) and not np.isnan(grid_z[i - 1, j]):
                    slope_y[i, j] = (grid_z[i + 1, j] - grid_z[i - 1, j]) / (2 * step_y)

    slope_x_urad = slope_x * 1e6
    slope_y_urad = slope_y * 1e6

    tilt_urad_grid = np.full_like(slope_x_urad, np.nan)
    mask_both = ~np.isnan(slope_x_urad) & ~np.isnan(slope_y_urad)
    tilt_urad_grid[mask_both] = np.sqrt(
        slope_x_urad[mask_both] ** 2 + slope_y_urad[mask_both] ** 2
    )

    mask_only_x = ~np.isnan(slope_x_urad) & np.isnan(slope_y_urad)
    tilt_urad_grid[mask_only_x] = np.abs(slope_x_urad[mask_only_x])

    mask_only_y = np.isnan(slope_x_urad) & ~np.isnan(slope_y_urad)
    tilt_urad_grid[mask_only_y] = np.abs(slope_y_urad[mask_only_y])

    tilt_urad = tilt_urad_grid[row_indices, col_indices]
    return tilt_urad


def calculate_nce(x, y, z, field_size_x=0.026, field_size_y=0.008, offset_x=0.0):
    """计算NCE(非可校正误差),对每个场移除局部倾斜"""
    z_nce = np.full_like(z, np.nan)

    min_x, max_x = np.min(x), np.max(x)
    min_y, max_y = np.min(y), np.max(y)

    # 从数据推断物理间距
    x_sorted = np.sort(np.unique(x))
    y_sorted = np.sort(np.unique(y))
    step_x = np.median(np.diff(x_sorted)) if len(x_sorted) > 1 else (max_x - min_x)
    step_y = np.median(np.diff(y_sorted)) if len(y_sorted) > 1 else (max_y - min_y)

    start_x = min_x + offset_x
    n_cols = int(np.ceil((max_x - start_x) / field_size_x)) + 1
    n_rows = int(np.ceil((max_y - min_y) / field_size_y))

    x_edges = start_x + np.arange(n_cols + 1) * field_size_x
    y_edges = min_y + np.arange(n_rows + 1) * field_size_y

    grid_lines_x = x_edges
    grid_lines_y = y_edges

    expected_points = (field_size_x * field_size_y) / (step_x * step_y)
    min_points = max(10, int(expected_points * 0.1))

    for i in range(len(x_edges) - 1):
        for j in range(len(y_edges) - 1):
            x_start, x_end = x_edges[i], x_edges[i + 1]
            y_start, y_end = y_edges[j], y_edges[j + 1]

            mask = (x >= x_start) & (x < x_end) & (y >= y_start) & (y < y_end)

            if np.sum(mask) > min_points:
                x_field = x[mask]
                y_field = y[mask]
                z_field = z[mask]

                A = np.c_[x_field, y_field, np.ones(len(x_field))]
                coeff, _, _, _ = np.linalg.lstsq(A, z_field, rcond=None)
                a, b, c = coeff
                z_fit = a * x_field + b * y_field + c

                z_nce[mask] = z_field - z_fit

    return z_nce, grid_lines_x, grid_lines_y


def plot_sfma_heatmap(x, y, z_sfma, metric_val, output_image_path):
    """生成SFMA热力图"""
    plt.figure(figsize=(8, 6))
    cmap = plt.get_cmap("jet")

    mask = ~np.isnan(z_sfma)
    if np.sum(mask) == 0:
        return

    cntr = plt.tricontourf(x[mask], y[mask], z_sfma[mask], levels=100, cmap=cmap)
    cbar = plt.colorbar(cntr)
    cbar.formatter.set_powerlimits((0, 0))

    r = np.max(np.sqrt(x**2 + y**2))
    circle = plt.Circle((0, 0), r, color="k", fill=False, linewidth=1)
    plt.gca().add_patch(circle)

    plt.axis("equal")
    plt.xlabel("X (m)")
    plt.ylabel("Y (m)")
    plt.title(f"SFMA\nm3s = {metric_val*1e9:.2f} nm")

    plt.savefig(output_image_path, dpi=300, bbox_inches="tight", pad_inches=0.1)
    plt.close()
    # print(f"Saved SFMA heatmap to {output_image_path}")


def plot_surface_heatmap(x, y, z_resid, pv, output_image_path):
    """生成去一阶面形后的热力图"""
    plt.figure(figsize=(8, 6))
    cmap = plt.get_cmap("jet")
    cntr = plt.tricontourf(x, y, z_resid, levels=100, cmap=cmap)
    cbar = plt.colorbar(cntr)
    cbar.formatter.set_powerlimits((0, 0))

    r = np.max(np.sqrt(x**2 + y**2))
    circle = plt.Circle((0, 0), r, color="k", fill=False, linewidth=1)
    plt.gca().add_patch(circle)

    plt.axis("equal")
    plt.xlabel("X (m)")
    plt.ylabel("Y (m)")
    plt.title(f"去一阶面形\nPV = {pv*1e6:.2f} um")

    plt.savefig(output_image_path, dpi=300, bbox_inches="tight", pad_inches=0.1)
    plt.close()
    # print(f"Saved heatmap to {output_image_path}")


def plot_tilt_heatmap(
    x, y, tilt_urad, mean_val, std_val, max_val, metric_val, output_image_path
):
    """生成局部倾斜角度热力图"""
    plt.figure(figsize=(8, 6))
    cmap = plt.get_cmap("jet")

    mask = ~np.isnan(tilt_urad)
    if np.sum(mask) == 0:
        print("No valid tilt data to plot.")
        return

    cntr = plt.tricontourf(x[mask], y[mask], tilt_urad[mask], levels=100, cmap=cmap)
    cbar = plt.colorbar(cntr)
    cbar.set_label("μrad")

    r = np.max(np.sqrt(x**2 + y**2))
    circle = plt.Circle((0, 0), r, color="k", fill=False, linewidth=1)
    plt.gca().add_patch(circle)

    plt.axis("equal")
    plt.xlabel("X (m)")
    plt.ylabel("Y (m)")
    plt.title(f"局部角分布\nmax= {max_val:.2f} μrad, m3s = {metric_val:.2f} μrad")

    plt.savefig(output_image_path, dpi=300, bbox_inches="tight", pad_inches=0.1)
    plt.close()
    # print(f"Saved tilt heatmap to {output_image_path}")


def plot_high_tilt_heatmap(x, y, tilt_urad, threshold, output_image_path):
    """生成大于特定阈值的局部倾斜角度热力图"""
    plt.figure(figsize=(8, 6))
    cmap = plt.get_cmap("jet")

    mask = (~np.isnan(tilt_urad)) & (tilt_urad > threshold)

    if np.sum(mask) == 0:
        # 如果没有超过阈值的点，生成一个空图或者提示图
        plt.text(
            0.5,
            0.5,
            f"No data > {threshold} μrad",
            horizontalalignment="center",
            verticalalignment="center",
            transform=plt.gca().transAxes,
        )
    else:
        # 使用 scatter 绘制散点，因为超过阈值的区域可能是不连续的
        sc = plt.scatter(x[mask], y[mask], c=tilt_urad[mask], cmap=cmap, s=5)
        cbar = plt.colorbar(sc)
        cbar.set_label("μrad")

    r = np.max(np.sqrt(x**2 + y**2))
    circle = plt.Circle((0, 0), r, color="k", fill=False, linewidth=1)
    plt.gca().add_patch(circle)

    plt.axis("equal")
    plt.xlabel("X (m)")
    plt.ylabel("Y (m)")
    plt.title(f"局部角分布 (大于{threshold}μrad区域)")

    plt.savefig(output_image_path, dpi=300, bbox_inches="tight", pad_inches=0.1)
    plt.close()
    # print(f"Saved high tilt heatmap to {output_image_path}")


def plot_nce_heatmap(x, y, z_nce, std_val, grid_x, grid_y, output_image_path):
    """生成NCE面形热力图"""
    plt.figure(figsize=(8, 6))
    cmap = plt.get_cmap("jet")

    mask = ~np.isnan(z_nce)
    if np.sum(mask) == 0:
        print("No valid NCE data to plot.")
        return

    cntr = plt.tricontourf(x[mask], y[mask], z_nce[mask], levels=100, cmap=cmap)
    cbar = plt.colorbar(cntr)
    cbar.formatter.set_powerlimits((0, 0))

    for gx in grid_x:
        plt.axvline(gx, color="k", linewidth=0.5)
    for gy in grid_y:
        plt.axhline(gy, color="k", linewidth=0.5)

    r = np.max(np.sqrt(x**2 + y**2))
    circle = plt.Circle((0, 0), r, color="k", fill=False, linewidth=1)
    plt.gca().add_patch(circle)

    plt.axis("equal")
    plt.xlabel("X (m)")
    plt.ylabel("Y (m)")
    plt.title(f"NCE面形（96场布局）\n3std = {3*std_val*1e9:.2f} nm")

    plt.savefig(output_image_path, dpi=300, bbox_inches="tight", pad_inches=0.1)
    plt.close()
    # print(f"Saved NCE heatmap to {output_image_path}")


def process_xyz(
    input_path,
    output_path,
    scale=0.000175,
    step_x=0.0034,
    step_y=0.0005,
    slit_height=0.008,
):
    """
    处理XYZ文件并生成分析结果

    Args:
        input_path: 输入XYZ文件路径
        output_path: 输出文件路径
        scale: 原始数据分辨率,单位米 (默认: 0.000175m = 0.175mm)
        step_x: X方向子口径尺寸,单位米 (默认: 0.0034m = 3.4mm)
        step_y: Y方向子口径尺寸,单位米 (默认: 0.0005m = 0.5mm)
        slit_height: 调平狭缝宽度,单位米 (默认: 0.008m = 8mm)
    """
    # print(f"Processing {input_path} -> {output_path}")
    # print(
    #     f"Parameters: scale={scale}m, step_x={step_x}m, step_y={step_y}m, slit_height={slit_height}m"
    # )

    SCALE = scale
    STEP_X = step_x
    STEP_Y = step_y

    # 第一遍: 读取数据确定中心和边界
    # print("First pass: Reading data to determine center and bounds...")

    with open(input_path, "r") as f:
        lines = f.readlines()

    # print(f"Read {len(lines)} lines from input.")

    raw_data = []
    for line in lines[14:]:
        parts = line.strip().split()
        if len(parts) < 3:
            continue

        try:
            ix = int(parts[0])
            iy = int(parts[1])
            if parts[2] == "No":
                continue
            z_um = float(parts[2])
            raw_data.append((ix, iy, z_um))
        except ValueError:
            continue

    # print(f"Found {len(raw_data)} valid data points.")

    if len(raw_data) == 0:
        print("Error: No valid data points found in input file!")
        return None

    # 计算中心点(数据范围的中点)
    ix_values = [d[0] for d in raw_data]
    iy_values = [d[1] for d in raw_data]

    min_ix, max_ix = min(ix_values), max(ix_values)
    min_iy, max_iy = min(iy_values), max(iy_values)

    CENTER_IX = (min_ix + max_ix) / 2.0
    CENTER_IY = (min_iy + max_iy) / 2.0

    # print(f"Calculated center: CENTER_IX={CENTER_IX:.1f}, CENTER_IY={CENTER_IY:.1f}")
    # print(f"Data range: ix=[{min_ix}, {max_ix}], iy=[{min_iy}, {max_iy}]")

    # 第二遍: 转换到物理坐标并分箱
    # print("Second pass: Converting to physical coordinates and binning...")

    physical_points = []
    for ix, iy, z_um in raw_data:
        x = (ix - CENTER_IX) * SCALE
        y = (CENTER_IY - iy) * SCALE
        z_m = z_um * 1e-6
        physical_points.append((x, y, z_m))

    x_coords = [p[0] for p in physical_points]
    y_coords = [p[1] for p in physical_points]

    min_x, max_x = min(x_coords), max(x_coords)
    min_y, max_y = min(y_coords), max(y_coords)

    START_X = np.floor(min_x / STEP_X) * STEP_X
    START_Y = np.floor(min_y / STEP_Y) * STEP_Y

    # print(
    #     f"Physical bounds: x=[{min_x:.6f}, {max_x:.6f}], y=[{min_y:.6f}, {max_y:.6f}]"
    # )
    # print(f"Grid starts: START_X={START_X:.6f}, START_Y={START_Y:.6f}")

    # 数据分箱
    bins = {}
    data_count = 0

    for x, y, z_m in physical_points:
        k_x = int(round((x - START_X) / STEP_X))
        k_y = int(round((y - START_Y) / STEP_Y))
        key = (k_x, k_y)

        if key not in bins:
            bins[key] = [0.0, 0]

        bins[key][0] += z_m
        bins[key][1] += 1
        data_count += 1

    # print(f"Binned {data_count} data points into {len(bins)} bins.")

    # 输出处理后的数据
    plot_x, plot_y, plot_z = [], [], []
    sorted_keys = sorted(bins.keys(), key=lambda k: (k[1], k[0]))

    with open(output_path, "w") as f:
        for k_x, k_y in sorted_keys:
            grid_x = START_X + k_x * STEP_X
            grid_y = START_Y + k_y * STEP_Y
            sum_z, count = bins[(k_x, k_y)]
            avg_z = sum_z / count

            f.write(f"{grid_x:.15f} {grid_y:.15f} {avg_z:.15f}\n")
            plot_x.append(grid_x)
            plot_y.append(grid_y)
            plot_z.append(avg_z)

    # print(f"Saved processed data to {output_path}")

    # 可视化分析
    if len(plot_x) > 0:
        x_arr = np.array(plot_x)
        y_arr = np.array(plot_y)
        z_arr = np.array(plot_z)

        # 1. 去一阶面形
        z_resid, pv = calculate_surface_form(x_arr, y_arr, z_arr)

        image_path = output_path.replace(".txt", ".png")
        plot_surface_heatmap(x_arr, y_arr, z_resid, pv, image_path)

        # 2. NCE分析
        z_nce, _, _ = calculate_nce(
            x_arr, y_arr, z_arr, field_size_x=0.026, field_size_y=0.008
        )

        valid_nce = z_nce[~np.isnan(z_nce)]
        mean_nce = np.median(valid_nce)
        std_raw = np.std(valid_nce)

        mask_sigma = np.abs(valid_nce - mean_nce) <= 3 * std_raw
        filtered_nce = valid_nce[mask_sigma]
        std_nce = np.std(filtered_nce)
        nce_metric = mean_nce + 3 * std_nce

        disp_field_x = 0.026
        disp_field_y = 0.033
        n_disp_cols = int(np.ceil(np.max(np.abs(x_arr)) / disp_field_x))
        n_disp_rows = int(np.ceil(np.max(np.abs(y_arr)) / disp_field_y))

        gx = np.arange(-n_disp_cols, n_disp_cols + 1) * disp_field_x
        gy = np.arange(-n_disp_rows, n_disp_rows + 1) * disp_field_y

        nce_image_path = output_path.replace(".txt", "-nce.png")
        plot_nce_heatmap(x_arr, y_arr, z_nce, std_nce, gx, gy, nce_image_path)

        # 3. SFMA分析
        z_sfma = calculate_dynamic_sfma(
            x_arr,
            y_arr,
            z_resid,
            slit_h=slit_height,
        )

        valid_sfma = z_sfma[~np.isnan(z_sfma)]
        mean_sfma = np.median(valid_sfma)
        std_sfma_raw = np.std(valid_sfma)
        filtered_sfma = valid_sfma

        std_sfma = np.std(filtered_sfma)
        sfma_metric = np.median(filtered_sfma) + 3 * std_sfma
        sfma_image_path = output_path.replace(".txt", "-sfma.png")
        plot_sfma_heatmap(x_arr, y_arr, z_sfma, sfma_metric, sfma_image_path)

        # 4. 局部角分析
        tilt_urad = calculate_local_tilt(x_arr, y_arr, z_resid)

        valid_tilt = tilt_urad[~np.isnan(tilt_urad)]
        median_tilt = np.median(valid_tilt)
        std_tilt = np.std(valid_tilt)
        max_tilt = np.max(valid_tilt)
        tilt_metric = median_tilt + 3 * std_tilt

        tilt_image_path = output_path.replace(".txt", "-tilt.png")
        plot_tilt_heatmap(
            x_arr,
            y_arr,
            tilt_urad,
            median_tilt,
            std_tilt,
            max_tilt,
            tilt_metric,
            tilt_image_path,
        )

        # 5. 局部倾斜角度分析 (>12.5urad)
        high_tilt_image_path = output_path.replace(".txt", "-tilt-high.png")
        plot_high_tilt_heatmap(x_arr, y_arr, tilt_urad, 12.5, high_tilt_image_path)

        return {
            "pv": pv,  # 保留两位小数
            "nce": nce_metric,
            "sfma": sfma_metric,
            "tilt": tilt_metric,
        }


if __name__ == "__main__":
    process_xyz("005-avg.xyz", "005-avg-processed.txt")
