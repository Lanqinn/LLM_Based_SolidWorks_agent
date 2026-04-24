## 参考资料：https://mp.weixin.qq.com/s/xf_lDViBEt0IR-sxPlQVRA，特别是前面的makepy.py相关的操作


import win32com.client as win32
import pythoncom
import os  # noqa: F401
import lib

# 获取SW应用实例
sw_app = lib.get_solidworks_app()

# 获取版本信息以确认连接成功
print(f"SolidWorks 版本: {sw_app.RevisionNumber}")
# --- 2. 创建一个新的零件文档 ---
# 零件模板路径：通常是系统默认的，但最好指定完整的路径
# 这里我们使用一个通用的模板名称，SolidWorks会去搜索默认位置
template_path = rf"C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2024\templates\gb_part.prtdot"
swModel = lib.create_new_part_document(sw_app, template_path)

if swModel is None:
    exit()

# 2.3 执行拉伸建模 (圆柱体) - 使用毫米单位
lib.extrude_cylinder(
    swModel, 
    radius_m=0.025,  # 50mm 直径
    height_m=0.05,  # 50mm 高度
    center_x_m=0.0, 
    center_y_m=0.0
)

# 4. 在圆柱体中心切一个深 5mm，直径 20mm 的孔
cut_radius = 0.010  # 10mm 半径 (20mm 直径)
cut_depth_mm = 0.005

lib.create_cut_extrude_circle(swModel, 0, 0, cut_radius, mode="BLIND", depth_m=cut_depth_mm)

# --- 4. 保存文档 (可选) ---
save_path = rf"C:\Users\Free\Desktop\SW宏\圆柱{cut_depth_mm}.SLDPRT" # 替换为你自己的路径
lib.save_document(swModel, save_path)

