######  每添加一个函数，就要在FUNCTION_MAP里补充，在系统提示词里面补充


import win32com.client as win32
import pythoncom
import os  # noqa: F401
import math
from win32com.client import VARIANT

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
    在指定面上创建一个圆柱体（拉伸实体）。优先在当前选中的面上创建；如果没有选中，则在 Top Plane 上创建
    所有输入参数均使用米 (m) 作为单位。
    
    Args:
        swModel: ModelDoc2 对象。
        radius_m: 圆柱体的半径（米）。
        height_m: 圆柱体的高度（米）。
        center_x_m: 圆心 X 坐标（米）。
        center_y_m: 圆心 Y 坐标（米）。
    """
    
    print(f"\n--- 开始创建拉伸实体：R={radius_m}m, H={height_m}m ---")

    # 1. 智能选择绘图平面
    sel_mgr = swModel.SelectionManager
    if sel_mgr.GetSelectedObjectCount2(-1) > 0:
        print(f"\n--- 👆 检测到已选面，将在【当前选择】上创建圆柱：R={radius_m}m, H={height_m}m ---")
        # 保持当前选择，直接插入草图
    else:
        print(f"\n--- 🌐 未检测到选择，将在【Top Plane】上创建圆柱：R={radius_m}m, H={height_m}m ---")
        swModel.ClearSelection2(True)
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
def create_cut_extrude_circle(swModel, radius_m, mode="THRU_ALL", depth_m=None, center_x: float = 0.0, center_y: float = 0.0, flip_direction: bool = False):
    """
    在当前活动零件的指定面上创建一个圆并进行拉伸切除 (基于 swModel.FeatureManager.FeatureCut4)。
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
    
    # 1. 智能选择绘图平面
    sel_mgr = swModel.SelectionManager
    if sel_mgr.GetSelectedObjectCount2(-1) > 0:
        print(f"\n--- 👆 检测到已选面，开始打孔: R={radius_m}m ---")
    else:
        print(f"\n--- 🌐 未检测到选择，在【Top Plane】上打孔 ---")
        swModel.ClearSelection2(True)
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


    # 6. 智能切除逻辑   创建拉伸切除特征 (FeatureCutExtrude2) - 23个参数
    # 记录切除前的特征数量
    feat_mgr = swModel.FeatureManager
    count_before = feat_mgr.GetFeatureCount(False)

    print(f"   👉 尝试第 1 次切除 (Flip={flip_direction})...")

    # 第一次尝试
    # 参数 3: flip_direction
    # 参考宏中的深度参数 0.004 m
    success = swModel.FeatureManager.FeatureCut4(
        True,               # 1. AutoSelect
        False,              # 2. SketchPlaneFlip
        flip_direction,               # 3. Direction
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
    
    # 检查结果
    count_after = feat_mgr.GetFeatureCount(False)
    success = False
    final_flip = flip_direction

    if count_after > count_before:
        success = True
        print(f"   ✅ 切除成功。")
    else:
        print(f"   ⚠️ 第 1 次切除未产生特征 (可能方向反了)。正在尝试自动翻转...")
        
        # 翻转方向
        final_flip = not flip_direction
        
        # 重新选中草图 (因为上次操作失败可能导致选择丢失)
        swModel.ClearSelection2(True)
        if swSketch:
            swSketch.Select2(False, 0)
        
        # 第二次尝试
        swModel.FeatureManager.FeatureCut4(
            True, False, 
            final_flip,     # <--- 翻转后的参数
            end_cond, 0, d1_value, 0.01, 
            False, False, False, False, 0.0174532925199433, 0.0174532925199433, 
            0, 0, 0, False, False, True, True, True, True, False, 0, 0, False, False
        )
        
        # 再次检查
        count_retry = feat_mgr.GetFeatureCount(False)
        if count_retry > count_before:
            success = True
            print(f"   ✅ 自动修复成功！(使用了 Flip={final_flip})")
        else:
            print(f"   ❌ 切除彻底失败 (正反向均无效)。")

    # 5. 结果处理
    swModel.ClearSelection2(True)
    # swModel.ViewZoomtofit2() # 可选：每次切完缩放

    if success:
         print(f"   ✅ [汇总] 拉伸切除成功！直径 {radius_m * 2:.3f}m, 模式: {mode_text}, Flip={final_flip}")
    
    return success





'''function: 拉伸矩形 (长方体)'''
def extrude_rectangle(swModel, length_m: float, width_m: float, height_m: float, center_x_m: float = 0.0, center_y_m: float = 0.0):
    """
    在 指定面上创建一个中心矩形并拉伸。
    Args:
        length_m: 矩形长度 (X方向)
        width_m:  矩形宽度 (Y方向)
        height_m: 拉伸高度
        center_x_m: 中心 X 坐标
        center_y_m: 中心 Y 坐标
    """

    sel_mgr = swModel.SelectionManager
    selected_face = None
    offset_x, offset_y = 0.0, 0.0

    # 自动获取当前选中面的中心（如果有）
    if sel_mgr.GetSelectedObjectCount2(-1) > 0:
        obj = sel_mgr.GetSelectedObject6(1, -1)
        if obj and hasattr(obj, "GetBox"): # 简单判断是否为面
            box = obj.GetBox
            # 计算面中心的全局坐标，用于偏移补偿（或者让模型理解这就是0,0）
            # 注意：最简单的逻辑是告诉模型：一旦选面，(0,0) 就是面的中心。
            print(f"--- 👆 在选中面上绘图，中心已重置为局部 (0,0) ---")
    else:
        swModel.Extension.SelectByID2("Top Plane", "PLANE", 0, 0, 0, False, 0, ARG_NOTHING, 0)

    swModel.SketchManager.InsertSketch(True)
    
    # 核心：使用中心矩形，默认 center_x_m, center_y_m 相对于草图原点
    corner_x = center_x_m + (length_m / 2)
    corner_y = center_y_m + (width_m / 2)
    swModel.SketchManager.CreateCenterRectangle(center_x_m, center_y_m, 0, corner_x, corner_y, 0)

    swSketch = swModel.SketchManager.ActiveSketch
    swModel.SketchManager.InsertSketch(True)
    
    if swSketch:
        swModel.ClearSelection2(True)
        swSketch.Select2(False, 0)

    # 执行拉伸
    success = swModel.FeatureManager.FeatureExtrusion2(
        1, 0, 0, 0, 0, height_m, height_m, 0, 0, 0, 0, 0.0, 0.0, 
        0, 0, 0, 0, 1, 1, 1, 0, 0, 0
    )

    if success:
        print("✅ 长方体创建成功。")
    else:
        print("❌ 长方体创建失败。")
    return success



'''function: 矩形切除'''
def create_cut_extrude_rectangle(swModel, length_m: float, width_m: float, mode="THRU_ALL", depth_m=None, center_x: float = 0.0, center_y: float = 0.0, flip_direction: bool = False):
    """
    在 指定面上创建矩形切除。
    """
    
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

    # 1. 智能选面
    sel_mgr = swModel.SelectionManager
    if sel_mgr.GetSelectedObjectCount2(-1) > 0:
        print(f"\n--- 👆 检测到已选面，开始矩形切除 ---")
    else:
        print(f"\n--- 🌐 未检测到选择，在【Top Plane】上切除 ---")
        swModel.ClearSelection2(True)
        swModel.Extension.SelectByID2("Top Plane", "PLANE", 0, 0, 0, False, 0, ARG_NOTHING, 0)  
    
    # 插入草图
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
    else:
        print("❌ 无法获取草图对象。")
        return False

    # --- 4. 智能切除逻辑 (核心修改) ---
    
    # 记录切除前的特征数量
    feat_mgr = swModel.FeatureManager
    count_before = feat_mgr.GetFeatureCount(False)

    print(f"   👉 尝试第 1 次切除 (Flip={flip_direction})...")
    
    # 第一次尝试
    # 参数 3: flip_direction
    swModel.FeatureManager.FeatureCut4(
        True, False, flip_direction, end_cond, 0, d1_value, 0.01, 
        False, False, False, False, 0.0, 0.0, 
        0, 0, 0, False, False, True, True, True, True, False, 0, 0, False, False
    )
    
    # 检查是否成功生成了特征
    count_after = feat_mgr.GetFeatureCount(False)
    
    success = False
    final_flip = flip_direction

    if count_after > count_before:
        success = True
        print(f"   ✅ 切除成功。")
    else:
        print(f"   ⚠️ 第 1 次切除未产生特征 (可能方向反了)。正在尝试自动翻转...")
        
        # 翻转方向
        final_flip = not flip_direction
        
        # 重新选中草图 (因为上次操作失败可能导致选择丢失)
        swModel.ClearSelection2(True)
        swSketch.Select2(False, 0)
        
        # 第二次尝试
        swModel.FeatureManager.FeatureCut4(
            True, False, final_flip, end_cond, 0, d1_value, 0.01, 
            False, False, False, False, 0.0, 0.0, 
            0, 0, 0, False, False, True, True, True, True, False, 0, 0, False, False
        )
        
        # 再次检查
        count_retry = feat_mgr.GetFeatureCount(False)
        if count_retry > count_before:
            success = True
            print(f"   ✅ 自动修复成功！(使用了 Flip={final_flip})")
        else:
            print(f"   ❌ 切除彻底失败 (正反向均无效)。")

    # --- 5. 结果处理 ---
    swModel.ClearSelection2(True)
    
    if success and mode == "BLIND":
        # 补充打印具体信息
        pass 
        
    return success




'''function: 选面'''
def select_face(swModel, direction="TOP", index=0, position_filter: list = None, append=False):
    """
    通用空间选面工具。
    逻辑：先按法向筛选，再按空间距离(position_filter)或坐标轴(index)排序。
    大模型先检索到每一个方向上的所有面，然后根据上一步的指定坐标的计算结果，选择最合适的面，在上面画图
    """
    direction = direction.upper()
    swModel.ForceRebuild3(False)

    if not append:
        swModel.ClearSelection2(True)

    dir_map = {
        "TOP":    ([0, 1, 0],  1, True),   "BOTTOM": ([0, -1, 0], 1, False),
        "RIGHT":  ([1, 0, 0],  0, True),   "LEFT":   ([-1, 0, 0], 0, False),
        "FRONT":  ([0, 0, 1],  2, True),   "BACK":   ([0, 0, -1], 2, False)
    }
    
    target_vec, sort_axis, sort_desc = dir_map.get(direction, ([0, 1, 0], 1, True))
    part_bodies = swModel.GetBodies2(0, True)
    candidates = [] 

    if part_bodies:
        for body in part_bodies:
            for face in body.GetFaces():
                norm = face.Normal
                if norm and (norm[0]*target_vec[0] + norm[1]*target_vec[1] + norm[2]*target_vec[2] > 0.95):
                    box = face.GetBox 
                    center = [(box[0]+box[3])/2, (box[1]+box[4])/2, (box[2]+box[5])/2]
                    
                    # 核心逻辑：如果提供了参考坐标，计算欧氏距离；否则使用原有的轴排序
                    if position_filter:
                        dist = math.sqrt(sum((center[i] - position_filter[i])**2 for i in range(3)))
                        candidates.append((dist, face, center))
                    else:
                        candidates.append((center[sort_axis], face, center))

    # 排序：有位置过滤按距离升序（取最近），否则按坐标轴排序
    if position_filter:
        candidates.sort(key=lambda x: x[0])
    else:
        candidates.sort(key=lambda x: x[0], reverse=sort_desc)

    if candidates and 0 <= index < len(candidates):
        target_face = candidates[index][1]
    
        target_face.Select4(append, ARG_NOTHING)
        return True
    
    swModel.ClearSelection2(True)
    return True




'''function: 撤销功能'''
def undo_last_step(swModel):
    """
    智能撤销功能：
    1. 如果当前有选中的对象（面/草图等），则取消选择。
    2. 如果当前没有选择，则删除特征树中最后一个特征（及其包含的草图）。
    """
    print("\n--- 🔙 执行撤销操作 ---")
    
    # 1. 优先处理：清除选择
    sel_mgr = swModel.SelectionManager
    if sel_mgr.GetSelectedObjectCount2(-1) > 0:
        swModel.ClearSelection2(True)
        print("   ✅ 撤销成功：已清除当前选中的对象。")
        return True

    # 2. 次级处理：删除最后一个特征
    # 遍历特征树找到最后一个特征
    current_feat = swModel.FirstFeature
    last_editable_feat = None
    
    while current_feat:
        # 获取下一个特征
        next_feat = current_feat.GetNextFeature()
        
        # 记录非空的特征
        # 过滤掉一些不想删的基础特征（可选），但通常最后添加的都是用户特征
        if current_feat:
            last_editable_feat = current_feat
            
        current_feat = next_feat

    if last_editable_feat:
        # 保护机制：防止删除基准面和原点
        type_name = last_editable_feat.GetTypeName2()
        if type_name in ["RefPlane", "OriginProfileFeature"]:
            print("   ❌ 撤销失败：无法删除基准面或原点。")
            return False

        print(f"   👉 正在删除最后一个特征: {last_editable_feat.Name} ({type_name})...")
        
        # 选中该特征
        swModel.ClearSelection2(True)
        last_editable_feat.Select2(False, 0)
        
        # 删除选中项
        # DeleteSelection2 参数: 1 = swDelete_Absorbed (同时删除被该特征吸收的草图)
        deleted = swModel.Extension.DeleteSelection2(1)
        
        if deleted:
            print("   ✅ 撤销成功：特征已删除。")
            return True
        else:
            print("   ❌ 撤销失败：SolidWorks 拒绝删除该特征。")
            return False
            
    print("   ⚠️ 没有可撤销的操作。")
    return False



'''function: 多边形拉伸'''
def extrude_polygon(swModel, sides: int, radius_m: float, height_m: float, center_x_m: float = 0.0, center_y_m: float = 0.0):
    """
    在指定面上创建一个正多边形并拉伸。
    Args:
        sides: 边数 (例如 6 为六边形)
        radius_m: 外接圆半径 (米)
    """
    print(f"\n--- 开始创建正 {sides} 边形拉伸：R={radius_m}m, H={height_m}m ---")
    
    # 1. 智能选面 (复用逻辑)
    sel_mgr = swModel.SelectionManager
    if sel_mgr.GetSelectedObjectCount2(-1) == 0:
        swModel.ClearSelection2(True)
        swModel.Extension.SelectByID2("Top Plane", "PLANE", 0, 0, 0, False, 0, ARG_NOTHING, 0)
    
    # 2. 绘图
    swModel.SketchManager.InsertSketch(True)
    # CreatePolygon 参数: Center X, Y, Z, Corner X, Y, Z, Sides, IsInscribed
    swModel.SketchManager.CreatePolygon(center_x_m, center_y_m, 0, center_x_m + radius_m, center_y_m, 0, sides, True)
    
    swSketch = swModel.SketchManager.ActiveSketch
    swModel.SketchManager.InsertSketch(True)
    
    if swSketch:
        swModel.ClearSelection2(True)
        swSketch.Select2(False, 0)

    # 3. 拉伸
    success = swModel.FeatureManager.FeatureExtrusion2(
        1, 0, 0, 0, 0, height_m, height_m, 0, 0, 0, 0, 0.0, 0.0, 
        0, 0, 0, 0, 1, 1, 1, 0, 0, 0
    )

    if success:
        print(f"✅ 正 {sides} 边形实体创建成功。")
    else:
        print(f"❌ 正 {sides} 边形实体创建失败。")
    return success



'''function: 多边形切除'''
def create_cut_extrude_polygon(swModel, sides: int, radius_m: float, mode="THRU_ALL", depth_m=None, center_x: float = 0.0, center_y: float = 0.0, flip_direction: bool = False):
    """创建多边形切除特征 (带智能反向重试逻辑)"""
    print(f"\n--- 开始创建正 {sides} 边形切除：R={radius_m}m ---")

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

    # 1. 智能选面
    sel_mgr = swModel.SelectionManager
    if sel_mgr.GetSelectedObjectCount2(-1) > 0:
        print(f"\n--- 👆 检测到已选面，开始矩形切除 ---")
    else:
        print(f"\n--- 🌐 未检测到选择，在【Top Plane】上切除 ---")
        swModel.ClearSelection2(True)
        swModel.Extension.SelectByID2("Top Plane", "PLANE", 0, 0, 0, False, 0, ARG_NOTHING, 0)  
 
    # ... (参数准备与选面逻辑同矩形切除) ...
    # 绘图部分:
    swModel.SketchManager.InsertSketch(True)
    swModel.SketchManager.CreatePolygon(center_x, center_y, 0, center_x + radius_m, center_y, 0, sides, True)
    swSketch = swModel.SketchManager.ActiveSketch
    swModel.SketchManager.InsertSketch(True)

# --- 4. 智能切除逻辑 (核心修改) ---
    # 记录切除前的特征数量
    feat_mgr = swModel.FeatureManager
    count_before = feat_mgr.GetFeatureCount(False)

    print(f"   👉 尝试第 1 次切除 (Flip={flip_direction})...")
    
    # 第一次尝试
    swModel.FeatureManager.FeatureCut4(
        True, False, flip_direction, end_cond, 0, d1_value, 0.01, 
        False, False, False, False, 0.0, 0.0, 
        0, 0, 0, False, False, True, True, True, True, False, 0, 0, False, False
    )
    
    # 检查是否成功生成了特征
    count_after = feat_mgr.GetFeatureCount(False)
    
    success = False
    final_flip = flip_direction

    if count_after > count_before:
        success = True
        print(f"   ✅ 切除成功。")
    else:
        print(f"   ⚠️ 第 1 次切除未产生特征 (可能方向反了)。正在尝试自动翻转...")
        # 翻转方向
        final_flip = not flip_direction
        
        # 重新选中草图 (因为上次操作失败可能导致选择丢失)
        swModel.ClearSelection2(True)
        swSketch.Select2(False, 0)
        
        # 第二次尝试
        swModel.FeatureManager.FeatureCut4(
            True, False, final_flip, end_cond, 0, d1_value, 0.01, 
            False, False, False, False, 0.0, 0.0, 
            0, 0, 0, False, False, True, True, True, True, False, 0, 0, False, False
        )
        
        # 再次检查
        count_retry = feat_mgr.GetFeatureCount(False)
        if count_retry > count_before:
            success = True
            print(f"   ✅ 自动修复成功！(使用了 Flip={final_flip})")
        else:
            print(f"   ❌ 切除彻底失败 (正反向均无效)。")

    # --- 5. 结果处理 ---
    swModel.ClearSelection2(True)
    
    if success and mode == "BLIND":
        # 补充打印具体信息
        pass 
        
    return success




'''function: 旋转生成实体'''
def revolve_rectangle_feature(swModel, width_m: float, height_m: float, offset_m: float = 0.0, angle_deg: float = 360.0):
    """
    创建一个旋转实体。
    原理：在当前平面绘制一个矩形轮廓，并以 Y 轴（或指定中心线）为轴旋转。
    Args:
        width_m: 轮廓宽度
        height_m: 轮廓高度
        offset_m: 轮廓中心距离旋转轴的距离（如果是0，则是实心轴）
        angle_deg: 旋转角度
    """
    print(f"\n--- 开始创建旋转实体：W={width_m}, H={height_m}, 角度={angle_deg} ---")
    
    # 1. 默认选择 Front Plane
    swModel.ClearSelection2(True)
    swModel.Extension.SelectByID2("Front Plane", "PLANE", 0, 0, 0, False, 0, ARG_NOTHING, 0)
    
    swModel.SketchManager.InsertSketch(True)
    
    # 2. 绘制旋转轴 (Y轴方向中心线)
    swModel.SketchManager.CreateCenterLine(0, -height_m, 0, 0, height_m, 0)
    
    # 3. 绘制矩形轮廓
    # 参数：Corner1(x,y,z), Corner2(x,y,z)
    swModel.SketchManager.CreateCornerRectangle(offset_m, -height_m/2, 0, offset_m + width_m, height_m/2, 0)
    
    swModel.SketchManager.InsertSketch(True)
    
    # 4. 执行旋转 (必须传满参数)
    angle_rad = angle_deg * (math.pi / 180.0)
    
    # FeatureRevolve2(SingleDir, IsSolid, RevolveType, Angle, Reverse, ...)
    success = swModel.FeatureManager.FeatureRevolve2(
        True,               # 1. SingleDir
        True,               # 2. IsSolid
        False,              # 3. IsThin
        False,              # 4. Reverse
        False,              # 5. BothDirections
        False,              # 6. Dir
        int(0),             # 7. Type1 (swEndCondBlind)
        int(0),             # 8. Type2
        angle_rad,          # 9. Angle1
        0.0,                # 10. Angle2
        False,              # 11. OffsetReverse1
        False,              # 12. OffsetReverse2
        0.0,                # 13. OffsetDistance1
        0.0,                # 14. OffsetDistance2
        int(0),             # 15. ThinType
        0.0,                # 16. ThinThickness1
        0.0,                # 17. ThinThickness2
        True,               # 18. Merge
        True,               # 19. UseFeatScope
        True                # 20. AutoSelect
    )
    
    swModel.ClearSelection2(True)

    if success is not None:
        print("✅ 旋转实体创建成功。")

    else:
        print("❌ 旋转实体创建失败。")
    return success





    
'''草图绘制，基本功能'''
'''function: 开启草图会话'''
def start_sketch(swModel):
    """在当前选定面上开启草图。如果没有选面，默认在 Top Plane。"""
    # 如果没选面，默认选 Top Plane
    sel_mgr = swModel.SelectionManager
    if sel_mgr.GetSelectedObjectCount2(-1) == 0:
        swModel.Extension.SelectByID2("Top Plane", "PLANE", 0, 0, 0, False, 0, ARG_NOTHING, 0)
    
    swModel.SketchManager.InsertSketch(True)
    print("✅ 进入草图模式")
    return True

'''function: 绘制直线'''
def sketch_line(swModel, x1, y1, x2, y2):
    if swModel.SketchManager.ActiveSketch is None:
        print("   ⚠️ 检测到未开启草图，正在自动补全 start_sketch 操作...")
        start_sketch(swModel)
    """绘制一条从 (x1, y1) 到 (x2, y2) 的直线。单位：米。"""
    line = swModel.SketchManager.CreateLine(x1, y1, 0, x2, y2, 0)
    return True if line else False






def get_last_sketch_name(swModel):
    """
    遍历特征树，返回最后创建的一个草图特征的名称。
    辅助函数，不需要放到tool_schema里面
    """
    feature_mgr = swModel.FeatureManager
    # 获取特征树中的第一个特征
    current_feat = swModel.FirstFeature
    last_sketch_name = None

    while current_feat:
        # "ProfileFeature" 是 SolidWorks 中草图的内部类型名称
        if current_feat.GetTypeName2 == "ProfileFeature":
            last_sketch_name = current_feat.Name
        
        current_feat = current_feat.GetNextFeature

    return last_sketch_name

'''function: 验证并拉伸实体'''
def extrude(swModel, height_m:float):
    """
    特征检索版拉伸：通过遍历特征树找到最近的草图，并进行拉伸。
    彻底解决“分开调用”导致的引用丢失问题。
    """
    print("\n--- 🚀 开始执行特征检索式拉伸 ---")

    # 1. 强制结束可能存在的草图编辑状态
    swModel.SketchManager.InsertSketch(True)

    # 2. 检索最后一个草图的名称
    sketch_name = get_last_sketch_name(swModel)
    
    if not sketch_name:
        print("❌ 错误：在特征树中未找到任何草图。")
        return False
    
    print(f"✅ 成功锁定目标草图: {sketch_name}")

    # 3. 仿照 VBA 逻辑进行强制选中
    swModel.ClearSelection2(True)
    is_selected = swModel.Extension.SelectByID2(
        sketch_name, "SKETCH", 0, 0, 0, False, 0, ARG_NOTHING, 0
    )

    if not is_selected:
        print(f"❌ 错误：无法选中目标草图 {sketch_name}")
        return False

    # 4. 执行拉伸调用
    success = swModel.FeatureManager.FeatureExtrusion2(
        1, 0, 0, 0, 0, float(height_m), float(height_m), 0, 0, 0, 0, 0.0, 0.0, 
        0, 0, 0, 0, 1, 1, 1, 0, 0, 0
    )


    if success:
        print(f"✅ 拉伸特征生成成功：{sketch_name}")
        return True
    else:
        print(f"❌ 拉伸失败：请检查草图 {sketch_name} 是否闭合或自相交。")
        return False



'''function: 样条曲线'''
def sketch_spline(swModel, points: list):
    """
    绘制样条曲线。兼容 SolidWorks 各种 API 版本。
    """
    print(f"   👉 正在尝试绘制样条曲线，共 {len(points)} 个控制点")
    
    try:
        # 1. 准备一维 Double 数组 [x1, y1, z1, x2, y2, z2, ...]
        point_data = []
        for p in points:
            point_data.extend([float(p[0]), float(p[1]), 0.0])
        
        # 2. 包装为变体数组
        from win32com.client import VARIANT
        import pythoncom
        v_points = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, point_data)
        
        # 3. 获取 SketchManager 引用
        sk_mgr = swModel.SketchManager
        
        # 4. 防御性 API 调用逻辑
        # 优先尝试 CreateSpline2 (在 2024 版本中更稳定)，第二个参数 False 表示非模拟模式
        spline = None
        try:
            print("   🔍 尝试使用 CreateSpline2...")
            spline = sk_mgr.CreateSpline2(v_points, False)
        except:
            print("   🔍 CreateSpline2 不可用，尝试 CreateSpline...")
            try:
                spline = sk_mgr.CreateSpline(v_points)
            except Exception as e:
                print(f"   ❌ 所有 Spline API 均调用失败: {e}")
                return False

        if spline:
            print("   ✅ 样条曲线绘制成功")
            return True
        else:
            print("   ❌ API 返回为空，样条曲线未生成 (请检查坐标点是否有效)")
            return False
            
    except Exception as e:
        print(f"   ❌ sketch_spline 发生未知异常: {e}")
        return False



'''function: 绘制旋转轴专用的中心线'''
def sketch_centerline(swModel, x1, y1, x2, y2):
    """
    在当前草图中绘制中心线（旋转轴）。
    """
    print(f"   👉 绘制中心线: ({x1}, {y1}) -> ({x2}, {y2})")
    # Z 轴固定为 0，因为是在 2D 草图中绘图
    line = swModel.SketchManager.CreateCenterLine(float(x1), float(y1), 0, float(x2), float(y2), 0)
    return True if line else False


'''function: 通用旋转'''
def revolve_sketch(swModel, angle_deg: float = 360.0, thickness_m: float = None):
    """
    通用旋转工具：支持实心旋转与薄壁旋转。
    thickness_m: 如果提供数值，则生成指定厚度的薄壁实体；如果为 None，则生成实心体。
    """
    # 1. 退出草图并选中目标草图
    swModel.SketchManager.InsertSketch(True)
    sketch_name = get_last_sketch_name(swModel)
    if not sketch_name:
        return False
        
    swModel.ClearSelection2(True)
    swModel.Extension.SelectByID2(sketch_name, "SKETCH", 0, 0, 0, False, 0, ARG_NOTHING, 0)

    angle_rad = angle_deg * (math.pi / 180.0)
    
    # 核心逻辑：根据是否提供厚度切换参数
    is_thin = False if thickness_m is None else True
    is_solid = True if thickness_m is None else False
    actual_thickness = float(thickness_m) if thickness_m else 0.0

    print(f"   👉 执行旋转：类型={'薄壁' if is_thin else '实心'}, 角度={angle_deg}°")

    # 调用 FeatureRevolve2
    success = swModel.FeatureManager.FeatureRevolve2(
        True,               # 1. SingleDir
        is_solid,           # 2. IsSolid (逻辑切换)
        is_thin,            # 3. IsThin (逻辑切换)
        False,              # 4. Reverse
        False,              # 5. BothDirections
        False,              # 6. Dir
        int(0),             # 7. Type1
        int(0),             # 8. Type2
        angle_rad,          # 9. Angle1
        0.0,                # 10. Angle2
        False,              # 11. OffsetReverse1
        False,              # 12. OffsetReverse2
        0.0,                # 13. OffsetDistance1
        0.0,                # 14. OffsetDistance2
        int(0),             # 15. ThinType
        actual_thickness,   # 16. ThinThickness1
        0.0,                # 17. ThinThickness2
        True,               # 18. Merge
        True,               # 19. UseFeatScope
        True                # 20. AutoSelect
    )
    
    if success:
        print(f"   ✅ 旋转操作成功完成")
    return True if success else False


'''function: 设置外观'''
def apply_visual_style(swModel, style_name: str):
    """
    内置外观库：无需外部文件，直接定义光学属性。
    参数数组格式: [R, G, B, 环境光, 漫反射, 镜面反射, 光泽度, 透明度, 发光度] (0.0 - 1.0)
    """
    # --- 基础外观库定义 ---
    appearance_library = {
        # 金属类
        "gold": [1.0, 0.8, 0.0, 0.5, 0.6, 1.0, 0.8, 0.0, 0.0],         # 黄金
        "silver": [0.9, 0.9, 0.9, 0.4, 0.5, 1.0, 0.9, 0.0, 0.0],       # 白银
        "chrome": [0.8, 0.8, 0.9, 0.3, 0.4, 1.0, 1.0, 0.0, 0.0],       # 铬合金/镜面
        
        # 宝石/玻璃类 (带透明度)
        "ruby": [1.0, 0.0, 0.0, 0.3, 0.6, 1.0, 0.7, 0.3, 0.0],         # 红宝石
        "sapphire": [0.1, 0.2, 1.0, 0.3, 0.6, 1.0, 0.7, 0.3, 0.0],     # 蓝宝石
        "emerald": [0.0, 0.8, 0.2, 0.3, 0.6, 1.0, 0.7, 0.3, 0.0],      # 祖母绿
        "clear_glass": [0.9, 0.9, 1.0, 0.2, 0.2, 1.0, 0.9, 0.8, 0.0],  # 透明玻璃
        
        # 塑料/常用类
        "red_plastic": [1.0, 0.0, 0.0, 0.4, 0.7, 0.2, 0.2, 0.0, 0.0],  # 红色塑料
        "blue_plastic": [0.0, 0.3, 1.0, 0.4, 0.7, 0.2, 0.2, 0.0, 0.0], # 蓝色塑料
        "black_matte": [0.1, 0.1, 0.1, 0.5, 0.4, 0.0, 0.0, 0.0, 0.0]   # 磨砂黑
    }

    print(f"\n--- ✨ 正在从库中应用外观: {style_name} ---")
    
    selected_props = appearance_library.get(style_name.lower())
    
    if not selected_props:
        print(f"   ⚠️ 库中未找到样式 '{style_name}'，将使用默认红色。")
        selected_props = appearance_library["red_plastic"]

    # 包装为 SolidWorks 要求的变体数组
    v_props = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, selected_props)
    
    try:
        # 应用光学属性
        swModel.MaterialPropertyValues = v_props
        
        # 视觉补强：尝试加载背景场景（场景文件通常比外观文件更容易在安装包中保留）
        # 如果这个也报错，可以注销掉下面这一行
        swModel.Extension.InsertScene(r"\scenes\01 basic scenes\11 white kitchen.p2s")
        
        swModel.GraphicsRedraw2()
        print(f"   ✅ 外观风格 '{style_name}' 应用成功。")
        return True
    except Exception as e:
        print(f"   ❌ 设置外观失败: {e}")
        return False


'''function: 倒圆角'''
def apply_fillet(swModel, radius_m: float):
    """
    参考宏逻辑：对当前选中的面或边应用等半径圆角。
    使用 FeatureManager.FeatureFillet3，这是最稳健的 programmatic API。
    """
    print(f"\n--- ✨ 正在执行倒圆角：R={radius_m*1000:.1f}mm ---")
    
    # 1. 强制刷新模型，确保选择集有效
    swModel.ForceRebuild3(False)
    
    # 2. 获取特征管理器
    feat_mgr = swModel.FeatureManager
    
    # 3. 调用 FeatureFillet3 (共 8 个关键参数)
    # 参数含义参考：
    # 1 (Type): swFeatureFillet_UniformRadius (等半径)
    # radius_m: 半径 (米)
    # 1 (Propagate): 传播到相切面 (宏中常用)
    # 0 (Wait): swFilletExclusive
    # 0 (Help Point): 辅助点
    # 1 (IsSymmetric): 对称
    # 0 (Setback): 倒角延伸
    # ARG_NOTHING: 变半径点数组 (此处传空)
    
    try:
        # 使用 win32com 的变体占位符 ARG_NOTHING
        new_feat = feat_mgr.FeatureFillet3(
            1.0,                  # 等半径类型
            float(radius_m),    # 半径
            1.0,                  # 自动传播
            0.0,                  # 模式
            0.0,                  # 辅助点
            1.0,                  # 对称
            0.0,                  # 延伸
            ARG_NOTHING         # 占位符
        )
        
        if new_feat:
            print(f"   ✅ 圆角特征 '{new_feat.Name}' 创建成功。")
            swModel.ClearSelection2(True)
            return True
        else:
            # 如果返回 None，通常是几何冲突（半径太大）
            print("   ⚠️ 圆角创建失败：请检查半径是否过大（例如超过了立方体边长的一半）。")
            return False
            
    except Exception as e:
        print(f"   ❌ API 调用发生严重错误: {e}")
        return False