"""
Zygo XYZ文件头解析器
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ZygoHeader:
    # ===== Line 1 =====
    file_type: str  # "Zygo XYZ Data File"
    format: int  # 1 = XYZ, 2 = ASCII

    # ===== Line 2 =====
    creator_soft: int  # 0=unknown,1=MetroPro,2=MetroBASIC,3=d2bug
    version_major: int
    version_minor: int
    version_patch: int
    software_date: str

    # ===== Line 3 — Intensity Rect =====
    intens_x: int
    intens_y: int
    intens_width: int
    intens_height: int
    num_buckets: int
    intens_range: int

    # ===== Line 4 — Phase Rect =====
    phase_x: int
    phase_y: int
    phase_width: int
    phase_height: int

    # ===== Line 5–7 =====
    comment: str
    part_serial_number: str
    part_number: str

    # ===== Line 8 — Physical calibration =====
    source: int  # 0=measured,1=generated
    interf_scale_factor: float  # reflection=0.5, transmission=1.0
    wavelength: float  # meter
    numeric_aperture: float
    obliquity_factor: float
    unused: int
    pixel_size: float  # meter
    timestamp: int  # unix seconds

    # ===== Line 9 — System =====
    camera_width: int
    camera_height: int
    system_type: int
    system_board: int
    system_serial: int
    instrument_id: int
    objective_name: str

    # ===== Line 10 — Acquisition =====
    acquire_mode: int
    intens_avgs: int
    pzt_cal: int
    pzt_gain: int
    pzt_gain_tol: int
    agc_on: int
    target_range: float
    light_level: float
    min_mod: int
    min_mod_pts: int

    # ===== Line 11 — Phase processing =====
    phase_res: int  # 0=4096, 1=32768
    phase_avgs: int
    min_area: int
    discon_action: int
    discon_filter: int
    connection_proc: int
    conn_order: int
    remove_tilt: int
    remove_bias: int

    # ===== Line 12 — System error =====
    subtract_sys_err: int
    sys_err_file: str

    # ===== Line 13 — Transmission =====
    refractive_index: float
    part_thickness: float  # meter

    # ===== Line 14 — Zoom (Format 2 only) =====
    zoom_desc: Optional[str] = None


def parse_zygo_header(input_path: str) -> Optional[ZygoHeader]:
    """
    解析Zygo XYZ文件头部

    Args:
        input_path: XYZ文件路径

    Returns:
        ZygoHeader对象，如果解析失败返回None
    """
    try:
        with open(input_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = [f.readline().strip() for _ in range(14)]

        # Line 1: "Zygo XYZ Data File - Format 1"
        line1_parts = lines[0].split()
        file_type = " ".join(line1_parts[:-2]) if len(line1_parts) > 2 else lines[0]
        format_num = int(line1_parts[-1]) if len(line1_parts) > 0 else 1

        # Line 2: creator_soft version_major version_minor version_patch "date"
        line2_parts = lines[1].split()
        creator_soft = int(line2_parts[0]) if len(line2_parts) > 0 else 0
        version_major = int(line2_parts[1]) if len(line2_parts) > 1 else 0
        version_minor = int(line2_parts[2]) if len(line2_parts) > 2 else 0
        version_patch = int(line2_parts[3]) if len(line2_parts) > 3 else 0
        software_date = " ".join(line2_parts[4:]) if len(line2_parts) > 4 else ""

        # Line 3: Intensity Rect
        line3_parts = lines[2].split()
        intens_x = int(line3_parts[0]) if len(line3_parts) > 0 else 0
        intens_y = int(line3_parts[1]) if len(line3_parts) > 1 else 0
        intens_width = int(line3_parts[2]) if len(line3_parts) > 2 else 0
        intens_height = int(line3_parts[3]) if len(line3_parts) > 3 else 0
        num_buckets = int(line3_parts[4]) if len(line3_parts) > 4 else 0
        intens_range = int(line3_parts[5]) if len(line3_parts) > 5 else 0

        # Line 4: Phase Rect
        line4_parts = lines[3].split()
        phase_x = int(line4_parts[0]) if len(line4_parts) > 0 else 0
        phase_y = int(line4_parts[1]) if len(line4_parts) > 1 else 0
        phase_width = int(line4_parts[2]) if len(line4_parts) > 2 else 0
        phase_height = int(line4_parts[3]) if len(line4_parts) > 3 else 0

        # Lines 5-7: Comments
        comment = lines[4].strip('"')
        part_serial_number = lines[5].strip('"')
        part_number = lines[6].strip('"')

        # Line 8: Physical calibration
        line8_parts = lines[7].split()
        source = int(line8_parts[0]) if len(line8_parts) > 0 else 0
        interf_scale_factor = float(line8_parts[1]) if len(line8_parts) > 1 else 0.0
        wavelength = float(line8_parts[2]) if len(line8_parts) > 2 else 0.0
        numeric_aperture = float(line8_parts[3]) if len(line8_parts) > 3 else 0.0
        obliquity_factor = float(line8_parts[4]) if len(line8_parts) > 4 else 0.0
        unused = int(line8_parts[5]) if len(line8_parts) > 5 else 0
        pixel_size = float(line8_parts[6]) if len(line8_parts) > 6 else 0.0
        timestamp = int(line8_parts[7]) if len(line8_parts) > 7 else 0

        # Line 9: System
        line9_parts = lines[8].split()
        camera_width = int(line9_parts[0]) if len(line9_parts) > 0 else 0
        camera_height = int(line9_parts[1]) if len(line9_parts) > 1 else 0
        system_type = int(line9_parts[2]) if len(line9_parts) > 2 else 0
        system_board = int(line9_parts[3]) if len(line9_parts) > 3 else 0
        system_serial = int(line9_parts[4]) if len(line9_parts) > 4 else 0
        instrument_id = int(line9_parts[5]) if len(line9_parts) > 5 else 0
        objective_name = " ".join(line9_parts[6:]) if len(line9_parts) > 6 else ""

        # Line 10: Acquisition
        line10_parts = lines[9].split()
        acquire_mode = int(line10_parts[0]) if len(line10_parts) > 0 else 0
        intens_avgs = int(line10_parts[1]) if len(line10_parts) > 1 else 0
        pzt_cal = int(line10_parts[2]) if len(line10_parts) > 2 else 0
        pzt_gain = int(line10_parts[3]) if len(line10_parts) > 3 else 0
        pzt_gain_tol = int(line10_parts[4]) if len(line10_parts) > 4 else 0
        agc_on = int(line10_parts[5]) if len(line10_parts) > 5 else 0
        target_range = float(line10_parts[6]) if len(line10_parts) > 6 else 0.0
        light_level = float(line10_parts[7]) if len(line10_parts) > 7 else 0.0
        min_mod = int(line10_parts[8]) if len(line10_parts) > 8 else 0
        min_mod_pts = int(line10_parts[9]) if len(line10_parts) > 9 else 0

        # Line 11: Phase processing
        line11_parts = lines[10].split()
        phase_res = int(line11_parts[0]) if len(line11_parts) > 0 else 0
        phase_avgs = int(line11_parts[1]) if len(line11_parts) > 1 else 0
        min_area = int(line11_parts[2]) if len(line11_parts) > 2 else 0
        discon_action = int(line11_parts[3]) if len(line11_parts) > 3 else 0
        discon_filter = int(line11_parts[4]) if len(line11_parts) > 4 else 0
        connection_proc = int(line11_parts[5]) if len(line11_parts) > 5 else 0
        conn_order = int(line11_parts[6]) if len(line11_parts) > 6 else 0
        remove_tilt = int(line11_parts[7]) if len(line11_parts) > 7 else 0
        remove_bias = int(line11_parts[8]) if len(line11_parts) > 8 else 0

        # Line 12: System error
        line12_parts = lines[11].split()
        subtract_sys_err = int(line12_parts[0]) if len(line12_parts) > 0 else 0
        sys_err_file = " ".join(line12_parts[1:]) if len(line12_parts) > 1 else ""

        # Line 13: Transmission
        line13_parts = lines[12].split()
        refractive_index = float(line13_parts[0]) if len(line13_parts) > 0 else 0.0
        part_thickness = float(line13_parts[1]) if len(line13_parts) > 1 else 0.0

        # Line 14: Zoom (optional, format 2 only)
        zoom_desc = lines[13] if len(lines) > 13 else None

        return ZygoHeader(
            file_type=file_type,
            format=format_num,
            creator_soft=creator_soft,
            version_major=version_major,
            version_minor=version_minor,
            version_patch=version_patch,
            software_date=software_date,
            intens_x=intens_x,
            intens_y=intens_y,
            intens_width=intens_width,
            intens_height=intens_height,
            num_buckets=num_buckets,
            intens_range=intens_range,
            phase_x=phase_x,
            phase_y=phase_y,
            phase_width=phase_width,
            phase_height=phase_height,
            comment=comment,
            part_serial_number=part_serial_number,
            part_number=part_number,
            source=source,
            interf_scale_factor=interf_scale_factor,
            wavelength=wavelength,
            numeric_aperture=numeric_aperture,
            obliquity_factor=obliquity_factor,
            unused=unused,
            pixel_size=pixel_size,
            timestamp=timestamp,
            camera_width=camera_width,
            camera_height=camera_height,
            system_type=system_type,
            system_board=system_board,
            system_serial=system_serial,
            instrument_id=instrument_id,
            objective_name=objective_name,
            acquire_mode=acquire_mode,
            intens_avgs=intens_avgs,
            pzt_cal=pzt_cal,
            pzt_gain=pzt_gain,
            pzt_gain_tol=pzt_gain_tol,
            agc_on=agc_on,
            target_range=target_range,
            light_level=light_level,
            min_mod=min_mod,
            min_mod_pts=min_mod_pts,
            phase_res=phase_res,
            phase_avgs=phase_avgs,
            min_area=min_area,
            discon_action=discon_action,
            discon_filter=discon_filter,
            connection_proc=connection_proc,
            conn_order=conn_order,
            remove_tilt=remove_tilt,
            remove_bias=remove_bias,
            subtract_sys_err=subtract_sys_err,
            sys_err_file=sys_err_file,
            refractive_index=refractive_index,
            part_thickness=part_thickness,
            zoom_desc=zoom_desc,
        )

    except Exception as e:
        print(f"解析Zygo文件头失败: {e}")
        return None
