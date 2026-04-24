######  每添加一个函数，就要在FUNCTION_MAP里补充，在系统提示词里面补充


import win32com.client as win32
import pythoncom
import os  # noqa: F401

# 全局变量
ARG_NOTHING = win32.VARIANT(pythoncom.VT_DISPATCH, None)


'''function获取 SolidWorks 应用程序对象'''
def get_solidworks_app():
    """连接到已运行的SolidWorks实例，或启动一个新实例。"""
    
    # 获取SolidWorks Application ProgID (例如 "SldWorks.Application")
    # 这个ProgID可能会随着SolidWorks版本变化，但通常是SldWorks.Application
    sw_prog_id = "SldWorks.Application"
    
    try:
        # 尝试连接到已运行的SolidWorks实例
        sw_app = win32.GetActiveObject(sw_prog_id)
        print("✅ 已成功连接到当前正在运行的 SolidWorks 实例。")
    except Exception:
        # 如果没有运行，则启动一个新的SolidWorks实例
        print("⚠️ 正在启动一个新的 SolidWorks 实例...")
        sw_app = win32.Dispatch(sw_prog_id)
        print("✅ SolidWorks 启动完成。")

    # 确保SW窗口可见 (可选)
    sw_app.Visible = True
    
    return sw_app


def create_new_part_document(sw_app, template_path: str):
    """
    创建一个新的零件文档 (Part Document) 并返回 ModelDoc2 对象。
    Args:
        sw_app: SolidWorks 应用程序对象。
        template_path: 零件模板的完整路径。
    """
    # 2: MMGS (毫米/克/秒) 单位制
    sw_doc = sw_app.NewDocument(
        template_path, 
        2, 
        0.0,
        0.0
    )
    if sw_doc is None:
        print("❌ 无法创建新的 SolidWorks 文档。请检查模板路径是否正确！")
        return None
    # 将文档对象转换为 ModelDoc2 对象
    swModel = sw_app.ActiveDoc
    print(f"✅ 已创建新的零件文档")
    return swModel


'''function 保存'''
def save_document(swModel, save_path: str):
    """保存当前活动的 SolidWorks 文档。"""
    try:
        swModel.SaveAs3(save_path, 0, 0) # 0: 正常保存
        print(f"✅ 文件已保存至: {save_path}")
        return True
    except Exception as e:
        print(f"❌ 文件保存失败: {e}")
        return False


'''function: 圆柱拉伸'''
def extrude_cylinder(swModel, radius_m: float, height_m: float, center_x_m: float = 0.0, center_y_m: float = 0.0):
    """
    在 Top Plane 上创建一个圆柱体（拉伸实体）。
    所有输入参数均使用米 (m) 作为单位。
    
    Args:
        swModel: ModelDoc2 对象。
        radius_m: 圆柱体的半径（米）。
        height_m: 圆柱体的高度（米）。
        center_x_m: 圆心 X 坐标（米）。
        center_y_m: 圆心 Y 坐标（米）。
    """
    
    swModel.ClearSelection2(True)
    print(f"\n--- 开始创建拉伸实体：R={radius_m}m, H={height_m}m ---")

    # 1. 选择 Top Plane 作为草图平面
    swModel.Extension.SelectByID2("Top Plane", "PLANE", 0, 0, 0, False, 0, ARG_NOTHING, 0)

    # 2. 进入草图模式
    swModel.SketchManager.InsertSketch(True)

    # 3. 绘制一个圆 (CreateCircle)
    swModel.SketchManager.CreateCircle(center_x_m, center_y_m, 0, center_x_m + radius_m, center_y_m, 0)

    # 🔴 关键修复步骤 A：获取当前草图对象
    swSketch = swModel.SketchManager.ActiveSketch
    
    if swSketch is None:
        print("❌ 错误：无法获取活动草图对象！")
        return False

    # 4. 退出草图
    swModel.SketchManager.InsertSketch(True)
    
    # 5. 选择草图实体 (Sketch)
    # 🔴 关键修复步骤 B：显式选中刚才那个草图对象
    swModel.ClearSelection2(True) # 先清除其他杂乱选择
    swSketch.Select2(False, 0)    # 选中我们的草图


    # --- 6. 创建拉伸特征 (FeatureExtrusion2 - 23 参数) ---
    # 宏中的深度和偏移值
    angle_value = 0.0 # 弧度 默认值，不带拔模
    success = swModel.FeatureManager.FeatureExtrusion2(
    # 1-7: 主要方向和偏移
    1,          # 1. AutoSelect (True)
    0,          # 2. DirType (swExtrudeDirection_Blind)
    0,          # 3. Dir (False)
    0,          # 4. T1 (swEndCondBlind)
    0,          # 5. StartOffsetType (swStartOffsetType_None)
    height_m, # 6. D1 (深度 10mm)
    height_m, # 7. StartOffsetValue (10mm - 宏中深度和偏移值相同)

    # 8-13: 选项
    0,          # 8. Flip
    0,          # 9. Draft
    0,          # 10. Offset
    0,          # 11. OffsetReverse
    angle_value, # 12. DraftAngle (弧度值)
    angle_value, # 13. OffsetValue (弧度值 - 宏中 DraftAngle 和 OffsetValue 相同)

    # 14-17: 终止条件和合并
    0,          # 14. UpToSurface
    0,          # 15. UpToVertex
    0,          # 16. UpToFace
    0,          # 17. Merge (False)

    # 18-20: 方向二
    1,          # 18. Dir2 (True)
    1,          # 19. T2 (swEndCondUpToNext)
    1,          # 20. D2 (swEndCondUpToNext)

    # 21-23: 范围和自动选择（Geometry scope）
    0,          # 21. FeatureScope
    0,          # 22. AutoSelect (swFeatureScope)
    0           # 23. NoMerge (False)
)
    
    swModel.ClearSelection2(True)
    # swModel.ViewZoomtofit2()
    
    if success:
        print("✅ 拉伸实体创建成功。")
    else:
        print("❌ 拉伸实体创建失败。")
        
    return success




'''function:圆柱切除'''
# --- 定义关键常量的值 ---
SW_END_COND_THROUGHALL = 1  # 完全贯穿 (ThroughAll)
SW_END_COND_BLIND = 0      # FeatureCut4 T1 参数值: 盲孔/指定深度
def create_cut_extrude_circle(swModel, radius_m, mode="THRU_ALL", depth_m=None, center_x: float = 0.0, center_y: float = 0.0):
    """
    在当前活动零件的 Top Plane 上创建一个圆并进行拉伸切除 (基于 FeatureCutExtrude2)。
    Args:
        swModel (object): SolidWorks ModelDoc2 对象。
        radius_m (float): 圆的半径 (米)。
        mode:盲孔或者贯穿。
        depth_m (float): 切除的深度 (米)。
        center_x (float): 圆心 X 坐标 (米)。
        center_y (float): 圆心 Y 坐标 (米)。
        

    """
    # 清除现有选择
    swModel.ClearSelection2(True) 
    
    print("\n--- 开始创建拉伸切除特征 ---")
    if mode == "THRU_ALL":
        end_cond = SW_END_COND_THROUGHALL
        # 完全贯穿模式下，深度值被忽略，但需要一个占位符（米）。
        d1_value = 0.01 
        mode_text = "完全贯穿"
    elif mode == "BLIND" and depth_m is not None:
        end_cond = SW_END_COND_BLIND
        d1_value = depth_m
        mode_text = f"盲孔 ({depth_m:.0f}mm)"
    else:
        print("❌ 错误：模式或参数不正确。盲孔模式必须提供 depth_m。")
        return False
    
    # 1. 选择 Top Plane 作为草图平面
    swModel.Extension.SelectByID2("Top Plane", "PLANE", 0, 0, 0, False, 0, ARG_NOTHING, 0)
    
    # 2. 进入草图模式
    swModel.SketchManager.InsertSketch(True)
    
    # 3. 绘制一个圆 (以 radius_m 确定大小)
    # CreateCircle(Center_X, Center_Y, Center_Z, Outer_X, Outer_Y, Outer_Z)
    swModel.SketchManager.CreateCircle(center_x, center_y, 0, center_x + radius_m, center_y, 0)
    
    # 🔴 关键修复 A：获取草图对象
    swSketch = swModel.SketchManager.ActiveSketch

    # 4. 退出草图
    swModel.SketchManager.InsertSketch(True)
    
    # 🔴 关键修复 B：显式选中草图
    swModel.ClearSelection2(True)
    if swSketch:
        swSketch.Select2(False, 0)
    else:
        print("⚠️ 警告：无法捕获草图对象，尝试依赖自动选择...")
    # 6. 创建拉伸切除特征 (FeatureCutExtrude2) - 23个参数
    # 参考宏中的深度参数 0.004 m
    success = swModel.FeatureManager.FeatureCut4(
        True,               # 1. AutoSelect
        False,              # 2. SketchPlaneFlip
        True,               # 3. Direction
        end_cond,           # 4. T1 (终止条件，例如 4=ThroughAll)
        0,                  # 5. T2 (终止条件 2 - 不使用)
        d1_value,           # 6. D1 (深度 1 - 深度值在 ThroughAll 时被忽略)
        0.01,               # 7. D2 (深度 2 - 不使用)
        False,              # 8. FlipSideToCut
        False,              # 9. Draft
        False,              # 10. DraftOutward
        False,              # 11. Offset
        0.0174532925199433, # 12. DraftAngle (默认值)
        0.0174532925199433, # 13. OffsetValue (默认值)
        0,                  # 14. UpToSurface
        0,                  # 15. UpToVertex
        0,                  # 16. UpToFace
        False,              # 17. UseStartOffset
        False,              # 18. TranslateSurface
        True,               # 19. Merge (合并结果)
        True,               # 20. UseDirection1
        True,               # 21. UseDirection2
        True,               # 22. FeatureScope
        False,              # 23. AutoSelect (FeatureScope AutoSelect)
        0,                  # 24. ScopeEntityCount
        0,                  # 25. ScopeFeatureCount
        False,              # 26. NoMerge
        False               # 27. FlipEndCon1
    )
    
    swModel.ClearSelection2(True)
    swModel.ViewZoomtofit2()

    if success:
    # 修正后的打印语句：统一输出格式，只在盲孔模式下打印深度。
        if mode == "BLIND":
             # 打印出深度，以毫米为单位显示，方便用户检查
             print(f"✅ 拉伸切除成功！直径 {radius_m * 2:.3f}m, 模式: {mode_text}, 深度: {depth_m}m")
        else:
             print(f"✅ 拉伸切除成功！直径 {radius_m * 2:.3f}m, 模式: {mode_text}")
    else:
        print("❌ 切除失败！请检查 API 参数。")
    
    return success



'''function: 拉伸矩形 (长方体)'''
def extrude_rectangle(swModel, length_m: float, width_m: float, height_m: float, center_x_m: float = 0.0, center_y_m: float = 0.0):
    """
    在 Top Plane 上创建一个中心矩形并拉伸。
    Args:
        length_m: 矩形长度 (X方向)
        width_m:  矩形宽度 (Y方向)
        height_m: 拉伸高度
        center_x_m: 中心 X 坐标
        center_y_m: 中心 Y 坐标
    """
    swModel.ClearSelection2(True)
    print(f"\n--- 开始创建长方体：L={length_m}, W={width_m}, H={height_m} ---")

    # 1. 选择 Top Plane
    swModel.Extension.SelectByID2("Top Plane", "PLANE", 0, 0, 0, False, 0, ARG_NOTHING, 0)
    swModel.SketchManager.InsertSketch(True)

    # 2. 绘制中心矩形 (CreateCenterRectangle)
    # 参数: Center X, Y, Z, Corner X, Y, Z
    # 计算角点坐标用于确定矩形大小
    corner_x = center_x_m + (length_m / 2)
    corner_y = center_y_m + (width_m / 2)
    
    # 注意：CreateCenterRectangle 返回的是对象数组，不直接返回草图
    swModel.SketchManager.CreateCenterRectangle(center_x_m, center_y_m, 0, corner_x, corner_y, 0)

    # 获取当前草图
    swSketch = swModel.SketchManager.ActiveSketch
    
    # 3. 退出并选中草图
    swModel.SketchManager.InsertSketch(True)
    swModel.ClearSelection2(True)
    if swSketch:
        swSketch.Select2(False, 0)

    # 4. 拉伸特征
    success = swModel.FeatureManager.FeatureExtrusion2(
        1, 0, 0, 0, 0, height_m, height_m, # D1 & Offset
        0, 0, 0, 0, 0.0, 0.0,              # Options
        0, 0, 0, 0,                        # Terminations
        1, 1, 1,                           # Dir2
        0, 0, 0                            # Scope
    )

    if success:
        print("✅ 长方体创建成功。")
    else:
        print("❌ 长方体创建失败。")
    return success


'''function: 矩形切除'''
def create_cut_extrude_rectangle(swModel, length_m: float, width_m: float, mode="THRU_ALL", depth_m=None, center_x: float = 0.0, center_y: float = 0.0):
    """
    在 Top Plane 上创建矩形切除。
    """
    swModel.ClearSelection2(True)
    print(f"\n--- 开始创建矩形切除 ---")
    
    # 确定深度模式
    if mode == "THRU_ALL":
        end_cond = 1 # Through All
        d1_value = 0.01 
    elif mode == "BLIND" and depth_m is not None:
        end_cond = 0 # Blind
        d1_value = depth_m
    else:
        print("❌ 参数错误: Blind模式需要深度。")
        return False

    # 1. 选择 Top Plane
    swModel.Extension.SelectByID2("Top Plane", "PLANE", 0, 0, 0, False, 0, ARG_NOTHING, 0)
    swModel.SketchManager.InsertSketch(True)

    # 2. 绘制中心矩形
    corner_x = center_x + (length_m / 2)
    corner_y = center_y + (width_m / 2)
    swModel.SketchManager.CreateCenterRectangle(center_x, center_y, 0, corner_x, corner_y, 0)
    
    swSketch = swModel.SketchManager.ActiveSketch
    swModel.SketchManager.InsertSketch(True)
    
    swModel.ClearSelection2(True)
    if swSketch:
        swSketch.Select2(False, 0)

    # 3. 切除特征
    success = swModel.FeatureManager.FeatureCut4(
        True, False, True, end_cond, 0, d1_value, 0.01, 
        False, False, False, False, 0.0, 0.0, 
        0, 0, 0, False, False, True, True, True, True, False, 0, 0, False, False
    )
    
    if success:
        print("✅ 矩形切除成功。")
    else:
        print("❌ 矩形切除失败。")
    return success



