from openai import OpenAI
import json  
import lib
from typing import Dict, Any, List
import inspect
import ast  # 🌟 必须导入此模块
import re  # 必须导入正则表达式模块


# --- 1. 配置和客户端初始化 ---
# client = OpenAI(
#     api_key="515910d5fc3d4b219dca5e1955bcfbc0.BBS7k22L6svnfjEP",
#     base_url="https://open.bigmodel.cn/api/paas/v4/"
# )
client = OpenAI(api_key="sk-hhdlfuwibkcceysdqnszndquuyhuoaavvrdtnzqltttejdnt", 
                base_url="https://api.siliconflow.cn/v1")


# 定义工具描述 (Tools Schema)
# llm_connector.py

tools_schema = [
    # --- 1. 选面工具 ---
    # llm_connector.py

# --- 1. 选面工具 (升级版：支持多选) ---
    {
        "type": "function",
        "function": {
            "name": "select_face",
            "description": "空间几何选面工具。用于在绘图前选择平面，或者在倒圆角前选择目标面。\n⚠️ 多选规则：如果倒角需要选两个面（例如面圆角），第一次调用设 append=False，第二次调用设 append=True。",
            "parameters": {
                "type": "object",
                "properties": {
                    "direction": {
                        "type": "string",
                        "enum": ["TOP", "BOTTOM", "LEFT", "RIGHT", "FRONT", "BACK"],
                        "description": "目标面的法线朝向。"
                    },
                    "append": {
                        "type": "boolean",
                        "description": "是否追加选择。False=清除之前的选择只选这一个；True=保留之前的选择并追加这个面。默认为 False。",
                        "default": False
                    },
                    "mark": {
                        "type": "integer",
                        "description": "选择标记值。普通绘图选 0；倒圆角建议选 1。",
                        "default": 0
                    },
                    "position_filter": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "可选。目标面中心点的参考坐标 [x, y, z]。"
                    },
                    "index": {
                        "type": "integer",
                        "description": "可选。若不提供位置过滤，则按该轴向坐标排序选择（0为最外侧）。"
                    }
                },
                "required": ["direction"]
            }
        }
    },

    # --- 2. 圆柱拉伸 ---
    {
        "type": "function",
        "function": {
            "name": "extrude_cylinder",
            "description": "创建圆柱体。逻辑：如果在调用此工具前已经选中了一个面，将在该面上生成；否则默认在 Top Plane 生成。",
            "parameters": {
                "type": "object",
                "properties": {
                    "radius_m": {
                        "type": "number",
                        "description": "圆柱体的半径 (米)"
                    },
                    "height_m": {
                        "type": "number",
                        "description": "圆柱体的高度 (米)"
                    },
                    "center_x_m": {
                        "type": "number",
                        "description": "相对于绘图面的局部 X 坐标 (米)，默认为 0.0"
                    },
                    "center_y_m": {
                        "type": "number",
                        "description": "相对于绘图面的局部 Y 坐标 (米)，默认为 0.0"
                    }
                },
                "required": ["radius_m", "height_m"]
            }
        }
    },

    # --- 3. 圆孔切除 ---
    {
        "type": "function",
        "function": {
            "name": "create_cut_extrude_circle",
            "description": "切除圆形孔。逻辑：如果在调用此工具前已经选中了一个面，将在该面上打孔；否则默认在 Top Plane 打孔。",
            "parameters": {
                "type": "object",
                "properties": {
                    "radius_m": {
                        "type": "number",
                        "description": "切除圆的半径 (米)"
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["THRU_ALL", "BLIND"],
                        "description": "模式：'THRU_ALL' (贯穿) 或 'BLIND' (盲孔)"
                    },
                    "depth_m": {
                        "type": "number",
                        "description": "切除深度 (米)。当 mode 为 'BLIND' 时必须提供。"
                    },
                    "center_x": {
                        "type": "number",
                        "description": "相对于绘图面的局部 X 坐标 (米)"
                    },
                    "center_y": {
                        "type": "number",
                        "description": "相对于绘图面的局部 Y 坐标 (米)"
                    },
                    "flip_direction": {
                        "type": "boolean",
                        "description": "是否翻转切除方向。True=反向切除，False=正向切除。如果切除变成了切空气（没切到实体），通常需要改变这个值。"
                    }
                },
                "required": ["radius_m"]
            }
        }
    },

    # --- 4. 长方体拉伸 ---
    {
            "type": "function",
            "function": {
                "name": "extrude_rectangle",
                "description": "通用长方体拉伸工具。建模逻辑：1. height_m 是拉伸方向的长度（如立柱的高度）。2. 若之前调用过 select_face，则 center_x/y 是相对于该面中心的局部坐标；若未选面，则是在 Top Plane 上的世界坐标。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "length_m": {"type": "number", "description": "草图中的宽度 (X)"},
                        "width_m": {"type": "number", "description": "草图中的深度 (Y)"},
                        "height_m": {"type": "number", "description": "拉伸出来的长度 (Z/高度)"},
                        "center_x_m": {"type": "number", "description": "草图中心 X 偏移"},
                        "center_y_m": {"type": "number", "description": "草图中心 Y 偏移"}
                    },
                    "required": ["length_m", "width_m", "height_m"]
                }
            }
    },


    # --- 5. 矩形切除 ---
    {
        "type": "function",
        "function": {
            "name": "create_cut_extrude_rectangle",
            "description": "切除矩形孔。逻辑：如果在调用此工具前已经选中了一个面，将在该面上切除；否则默认在 Top Plane 切除。",
            "parameters": {
                "type": "object",
                "properties": {
                    "length_m": {
                        "type": "number",
                        "description": "切除矩形 X 方向长度 (米)"
                    },
                    "width_m": {
                        "type": "number",
                        "description": "切除矩形 Y 方向宽度 (米)"
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["THRU_ALL", "BLIND"],
                        "description": "模式：'THRU_ALL' (贯穿) 或 'BLIND' (盲孔)"
                    },
                    "depth_m": {
                        "type": "number",
                        "description": "切除深度 (米)。当 mode 为 'BLIND' 时必须提供。"
                    },
                    "center_x": {
                        "type": "number",
                        "description": "相对于绘图面的局部 X 坐标 (米)"
                    },
                    "center_y": {
                        "type": "number",
                        "description": "相对于绘图面的局部 Y 坐标 (米)"
                    },
                    "flip_direction": {
                        "type": "boolean",
                        "description": "是否翻转切除方向。True=反向切除，False=正向切除。通常在平面上向下挖孔需要根据法线判断。"
                    }
                },
                "required": ["length_m", "width_m"]
            }
        }
    },

    # --- 6. 撤销 ---
    {
        "type": "function",
        "function": {
            "name": "undo_last_step",
            "description": "撤销上一步操作。用途：1. 如果选错了面，调用此工具取消选择。2. 如果上一步建模建错了（比如位置不对），调用此工具可以删除刚刚生成的实体。无参数。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    # --- 7. 拉伸正多边形 ---
    {
        "type": "function",
        "function": {
            "name": "extrude_polygon",
            "description": "在指定平面上创建并拉伸正多边形实体（如六边形、五边形等）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "sides": {
                        "type": "integer",
                        "description": "多边形的边数（例如 6 代表六边形，3 代表等边三角形）。"
                    },
                    "radius_m": {
                        "type": "number",
                        "description": "外接圆半径（米）。"
                    },
                    "height_m": {
                        "type": "number",
                        "description": "拉伸高度（米）。"
                    },
                    "center_x_m": {
                        "type": "number",
                        "description": "中心点 X 坐标，默认为 0.0。"
                    },
                    "center_y_m": {
                        "type": "number",
                        "description": "中心点 Y 坐标，默认为 0.0。"
                    }
                },
                "required": ["sides", "radius_m", "height_m"]
            }
        }
    },
    # --- 8. 切除正多边形 ---
    {
        "type": "function",
        "function": {
            "name": "create_cut_extrude_polygon",
            "description": "在指定平面上通过正多边形草图进行拉伸切除（挖孔）。具备自动方向纠错功能。",
            "parameters": {
                "type": "object",
                "properties": {
                    "sides": {
                        "type": "integer",
                        "description": "多边形的边数。"
                    },
                    "radius_m": {
                        "type": "number",
                        "description": "多边形外接圆半径（米）。"
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["THRU_ALL", "BLIND"],
                        "description": "切除模式：'THRU_ALL' (完全贯穿) 或 'BLIND' (指定深度)。"
                    },
                    "depth_m": {
                        "type": "number",
                        "description": "切除深度（米），仅在 BLIND 模式下有效。"
                    },
                    "center_x": {
                        "type": "number",
                        "description": "中心 X 坐标。"
                    },
                    "center_y": {
                        "type": "number",
                        "description": "中心 Y 坐标。"
                    },
                    "flip_direction": {
                        "type": "boolean",
                        "description": "是否翻转切除方向。默认为 False。"
                    }
                },
                "required": ["sides", "radius_m"]
            }
        }
    },
    # --- 9. 矩形旋转生成 ---
    {
        "type": "function",
        "function": {
            "name": "revolve_rectangle_feature",
            "description": "通过旋转截面生成实体。适用于圆环、瓶子或轴类零件。",
            "parameters": {
                "type": "object",
                "properties": {
                    "width_m": {"type": "number", "description": "旋转截面的宽度"},
                    "height_m": {"type": "number", "description": "旋转截面的高度"},
                    "offset_m": {"type": "number", "description": "截面距离中心轴的距离。0代表实心，大于0代表中间有孔的环状物。"},
                    "angle_deg": {"type": "number", "description": "旋转角度，默认360"}
                },
                "required": ["width_m", "height_m", "offset_m"]
            }
        }
    },
    # --- 10. 新建草图 ---
    {
        "type": "function",
        "function": {
            "name": "start_sketch",
            "description": "在当前选定面上开始一个新草图会话。这是绘制复杂图形的第一步。",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    # --- 11. 在当前草图中画线 ---
    {
        "type": "function",
        "function": {
            "name": "sketch_line",
            "description": "在当前草图中画线。注意：要形成闭合图形，下一条线的起点必须是上一条线的终点。",
            "parameters": {
                "type": "object",
                "properties": {
                    "x1": {"type": "number"}, "y1": {"type": "number"},
                    "x2": {"type": "number"}, "y2": {"type": "number"}
                },
                "required": ["x1", "y1", "x2", "y2"]
            }
        }
    },
    # --- 12. 当前草图按指定高度拉伸 ---
    {
        "type": "function",
        "function": {
            "name": "extrude",
            "description": "把当前草图按指定高度拉伸。",
            "parameters": {
                "type": "object",
                "properties": {
                    "height_m": {"type": "number", "description": "拉伸高度"}
                },
                "required": ["height_m"]
            }
        }
    },
    # --- 13. 绘制样条曲线 (Spline) ---
    {
        "type": "function",
        "function": {
            "name": "sketch_spline",
            "description": "在当前草图中绘制平滑的样条曲线。适用于创建花瓶、酒杯等具有有机弧线的轮廓。注意：为了形成闭合实体，曲线的终点应能与其他线条连接回中心轴。",
            "parameters": {
                "type": "object",
                "properties": {
                    "points": {
                        "type": "array",
                        "description": "坐标点列表，格式为 [[x1, y1], [x2, y2], ...]。系统会自动在这些点之间生成平滑曲线。",
                        "items": {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": 2,
                            "maxItems": 2
                        }
                    }
                },
                "required": ["points"]
            }
        }
    },

    # --- 14. 通用旋转特征 (Revolve)生成实心回转体或薄壁壳体 ---
    {
        "type": "function",
        "function": {
            "name": "revolve_sketch",
            "description": "通用旋转建模工具。可以生成实心回转体或薄壁壳体。逻辑：如果不需要厚度（实心体），不传 thickness_m；如果需要生成空心外壳，请指定 thickness_m。",
            "parameters": {
                "type": "object",
                "properties": {
                    "angle_deg": {"type": "number", "description": "旋转角度，默认 360"},
                    "thickness_m": {
                        "type": "number", 
                        "description": "必选参数。如果提供，将生成该厚度的薄壁实体（米）。若不提供，则生成实心体。"
                    }
                },
                "required": ["angle_deg", "thickness_m"]
            }
        }
    },
    # ---  15
    {
        "type": "function",
        "function": {
            "name": "sketch_centerline",
            "description": "在当前草图中绘制中心线（构造线）。核心用途：1. 作为旋转特征（revolve_sketch）的旋转轴；2. 作为镜像或对齐的参考线。注意：旋转体建模时，必须先画中心线，再画截面轮廓。",
            "parameters": {
                "type": "object",
                "properties": {
                    "x1": {"type": "number", "description": "起点 X 坐标 (米)"},
                    "y1": {"type": "number", "description": "起点 Y 坐标 (米)"},
                    "x2": {"type": "number", "description": "终点 X 坐标 (米)"},
                    "y2": {"type": "number", "description": "终点 Y 坐标 (米)"}
                    },
                "required": ["x1", "y1", "x2", "y2"]
            }
        }
    },
    # --- 16. 外观展示 ---
    {
        "type": "function",
        "function": {
            "name": "apply_visual_style",
            "description": "从内置库中为零件应用视觉样式。可选样式：'gold'(黄金), 'silver'(白银), 'ruby'(红宝石), 'sapphire'(蓝宝石), 'clear_glass'(玻璃), 'red_plastic'(红塑料), 'black_matte'(磨砂黑)。",
            "parameters": {
                "type": "object",
                "properties": {
                    "style_name": {
                        "type": "string",
                        "enum": ["gold", "silver", "chrome", "ruby", "sapphire", "emerald", "clear_glass", "red_plastic", "blue_plastic", "black_matte"]
                    }
                },
                "required": ["style_name"]
            }
        }
    },

    # --- 17. 倒角 ---

    # --- 18. 线性阵列 ---
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "linear_pattern",
    #         "description": "对【上一步创建的特征】进行线性阵列。注意：此工具会自动选中上一个特征。你需要指定方向。",
    #         "parameters": {
    #             "type": "object",
    #             "properties": {
    #                 "direction_axis": {
    #                     "type": "string",
    #                     "enum": ["X", "Y", "Z", "Selected"],
    #                     "description": "阵列方向。X/Y/Z 代表尝试沿基准面/轴阵列（可能不太准）。'Selected' 代表沿当前选中的边线阵列。"
    #                 },
    #                 "distance_m": {"type": "number", "description": "阵列间距 (米)"},
    #                 "count": {"type": "integer", "description": "阵列总数量 (含本体)"}
    #             },
    #             "required": ["direction_axis", "distance_m", "count"]
    #         }
    #     }
    # },
    
    # --- 19. 圆周阵列 ---

    # --- 20. 创建 3D 文字 (新增) ---
    {
        "type": "function",
        "function": {
            "name": "create_3d_text",
            "description": "创建 3D 立体文字（凸起的浮雕文字）。注意：如果要刻字（凹陷），可以随后调用 create_cut_extrude... 但通常直接拉伸文字实体即可。会自动在指定位置居中生成。",
            "parameters": {
                "type": "object",
                "properties": {
                    "text_content": {
                        "type": "string",
                        "description": "要生成的文字内容（例如 'SW Agent'）。"
                    },
                    "font_height_m": {
                        "type": "number",
                        "description": "字体高度 (米)。建议值 0.01 ~ 0.1。"
                    },
                    "extrude_depth_m": {
                        "type": "number",
                        "description": "文字拉伸的厚度 (米)。"
                    },
                    "center_x_m": {
                        "type": "number",
                        "description": "文字中心的 X 坐标 (米)。"
                    },
                    "center_y_m": {
                        "type": "number",
                        "description": "文字中心的 Y 坐标 (米)。"
                    }
                },
                "required": ["text_content", "font_height_m", "extrude_depth_m"]
            }
        }
    },

]



FUNCTION_MAP = {
    "start_sketch": lib.start_sketch,

    # --- 基础拉伸与切除 ---
    "extrude": lib.extrude,   # 通用拉伸功能
    "extrude_cylinder": lib.extrude_cylinder,
    "create_cut_extrude_circle": lib.create_cut_extrude_circle,
    "extrude_rectangle": lib.extrude_rectangle,
    "create_cut_extrude_rectangle": lib.create_cut_extrude_rectangle,
    "extrude_polygon": lib.extrude_polygon,
    "create_cut_extrude_polygon": lib.create_cut_extrude_polygon,
    
    # --- 底层草图工具 ---
    "sketch_line": lib.sketch_line,
    "sketch_spline": lib.sketch_spline,

    
    # --- 旋转轴线 ---
    "sketch_centerline": lib.sketch_centerline,
    # --- 旋转执行器 ---
    "revolve_rectangle_feature": lib.revolve_rectangle_feature,
    "revolve_sketch": lib.revolve_sketch,

    # --- 辅助与撤销 ---
    "select_face": lib.select_face, 
    "undo_last_step": lib.undo_last_step,

    # 设置外观
    "apply_visual_style": lib.apply_visual_style,

    # 倒角

    # 阵列
    # "linear_pattern": lib.linear_pattern,
    # "circular_pattern": lib.circular_pattern,

    "create_3d_text": lib.create_3d_text,

}

# --- 3. LLM API 调用函数 ---

def get_llm_planner_output(user_input: str, system_prompt: str, model_name: str):
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ]
    
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            tools=tools_schema,       
            tool_choice="auto", 
            temperature=0.0
        )
        
        message = response.choices[0].message
        
        # 1. openAI的标准，优先检查 Tool Calls
        if message.tool_calls:
            print(f"⚡ LLM 触发了 {len(message.tool_calls)} 个工具调用。")
            steps = []
            for tool_call in message.tool_calls:
                func_name = tool_call.function.name
                raw_args = tool_call.function.arguments
                
                # --- 🛡️ 增强的参数解析逻辑 (容错机制) ---
                arguments = {}
                try:
                    # 尝试 1: 标准 JSON 解析
                    arguments = json.loads(raw_args)
                except json.JSONDecodeError as e:
                    print(f"⚠️ 标准 JSON 解析失败: {e}")
                    print(f"   [原始参数]: {raw_args}")
                    print("   -> 尝试使用 Python AST 解析 (处理单引号)...")
                    try:
                        # 尝试 2: Python 字面量解析 (处理 {'key': 'value'} 情况)
                        arguments = ast.literal_eval(raw_args)
                        print("   ✅ AST 解析成功！")
                    except Exception as e2:
                        print(f"❌ 严重错误: 参数无法解析。忽略此步骤。Errors: {e}, {e2}")
                        continue # 跳过这个损坏的步骤

                steps.append({
                    "function": func_name,
                    "parameters": arguments
                })
            
            return json.dumps({"steps": steps})
            
        # 2. 检查 content 中的文本 JSON (兼容旧习惯)
        elif message.content:
            print(f"\n[LLM 回复文本]: {message.content}\n")
            # 简单的清洗逻辑，尝试提取 markdown 里的 json
            content = message.content

            # ======= 新增：Kimi 标签格式兼容逻辑 (保持原有逻辑向下兼容) =======
            if "<|tool_calls_section_begin|>" in content:
                # 使用 \| 来转义正则中的竖线
                tag_pattern = r"<\|tool_call_begin\|>functions\.(.*?):.*?<\|tool_call_argument_begin\|>(.*?)<\|tool_call_end\|>"
                matches = re.findall(tag_pattern, content, re.DOTALL)
                
                if matches:
                    steps = []
                    for func_name, args_raw in matches:
                        try:
                            # 清洗可能的空白字符并解析
                            steps.append({
                                "function": func_name.strip(),
                                "parameters": json.loads(args_raw.strip())
                            })
                        except:
                            continue
                    if steps:
                        print(f"✅ 修正解析：成功提取 {len(steps)} 个 Kimi 建模步骤。")
                        return json.dumps({"steps": steps})

            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
             
            try:
                # 同样尝试双重解析
                try:
                    json_obj = json.loads(content.strip())
                except:
                    json_obj = ast.literal_eval(content.strip())
                    
                if "steps" in json_obj:
                    return json.dumps(json_obj)
            except:
                pass
        
        elif message.content:
            content = message.content
            print(f"\n[LLM 回复文本]: {content}\n")
            
            # --- 增强型提取逻辑 ---
            # 1. 使用正则匹配所有 ```json ... ``` 或 ``` ... ``` 块
            code_blocks = re.findall(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
            
            all_steps = []
            
            if code_blocks:
                for block in code_blocks:
                    block_clean = block.strip()
                    try:
                        # 尝试解析
                        data = json.loads(block_clean)
                        if isinstance(data, list):
                            all_steps.extend(data)
                        elif isinstance(data, dict):
                            if "steps" in data:
                                all_steps.extend(data["steps"])
                            else:
                                all_steps.append(data)
                    except Exception:
                        # 如果解析失败（比如漏了引号），尝试用 ast.literal_eval 修复单引号或简单格式错误
                        try:
                            data = ast.literal_eval(block_clean)
                            if isinstance(data, list): all_steps.extend(data)
                            elif isinstance(data, dict): all_steps.append(data)
                        except:
                            continue # 实在解析不了就跳过该块
                
                if all_steps:
                    print(f"✅ 成功从代码块中提取了 {len(all_steps)} 个步骤。")
                    return json.dumps({"steps": all_steps})



        print("⚠️ LLM 未生成任何有效指令。")
        return json.dumps({"steps": []})

    except Exception as e:
        print(f"❌ API 调用失败: {e}")
        # 打印完整的错误堆栈有助于调试
        import traceback
        traceback.print_exc()
        return json.dumps({"steps": []})




def dispatch_instructions(swModel: Any, llm_json_output: str) -> bool:
    """
    解析 LLM 输出的 JSON 指令序列，并在 SolidWorks 中执行建模操作。
    兼容 tools_schema 的各种返回情况。
    """
    
    # 🌟 调试：打印 LLM 到底返回了什么
    print(f"\n[DEBUG] LLM 原始输出:\n{llm_json_output}\n")
    
    try:
        data = json.loads(llm_json_output)
        instructions = data.get("steps")
        
        # 处理空步骤的情况（如果是聊天而非指令，tools 可能返回空列表）
        if instructions is None:
            print("❌ 解析后未找到有效的 'steps' 键。")
            return False
        
        if len(instructions) == 0:
            print("⚠️ LLM 未生成任何建模步骤。")
            return True

    except json.JSONDecodeError:
        print("❌ JSON 解析错误。")
        return False

    print("\n--- 🧠 Agent 规划完成，开始执行建模步骤 ---")

    for i, instruction in enumerate(instructions):
        # 兼容 function 字段或 name 字段
        # (OpenAI Tool Call 原始返回通常是 name，如果你在 connector 里转成了 function 也没问题，这里双重兼容)
        func_name = instruction.get("function") or instruction.get("name")
        params = instruction.get("parameters", {})
        
        if func_name in FUNCTION_MAP:
            target_func = FUNCTION_MAP[func_name]
            
            # --- 🛡️ 参数清洗与校验逻辑 🛡️ ---
            sig = inspect.signature(target_func)
            
            # 1. 识别有效参数 (排除 swModel)
            valid_args = [name for name in sig.parameters.keys() if name != 'swModel']
            
            # 2. 识别必填参数 (没有默认值的参数)
            required_args = {
                name for name, param in sig.parameters.items() 
                if param.default == inspect.Parameter.empty and name != 'swModel'
            }
            
            # 3. 构建清洗后的参数字典
            cleaned_params = {}
            for key, value in params.items():
                if key in valid_args:
                    cleaned_params[key] = value
                elif key in ["swModel", "self"]: 
                    continue # 忽略系统参数
                else:
                    # 即使使用了 tools_schema，保留这个警告也是好习惯
                    print(f"   ⚠️ [警告] 步骤 {i+1}: 自动移除多余参数 '{key}'")

            # 4. 检查是否缺少必填参数
            missing_keys = required_args - set(cleaned_params.keys())
            if missing_keys:
                print(f"❌ 步骤 {i+1} 错误: 函数 '{func_name}' 缺少必要参数: {missing_keys}")
                return False 

            # --- 🚀 执行逻辑 🚀 ---
            try:
                print(f"[{i+1}/{len(instructions)}] 正在执行: {func_name} (参数: {list(cleaned_params.keys())})...")
                
                # 🔴 关键点：一定要用 cleaned_params
                result = FUNCTION_MAP[func_name](swModel, **cleaned_params)
                
                if not result:
                    print(f"❌ 步骤 {i+1} 执行返回 False，建模中止。")
                    return False
                    
            except TypeError as e:
                print(f"❌ 步骤 {i+1} 代码执行异常: {e}")
                return False
            except Exception as e:
                print(f"❌ 步骤 {i+1} 发生未知错误: {e}")
                return False
                
        else:
            print(f"⚠️ 无法识别的函数名称: {func_name}，跳过此步骤。")
            
    print("✅ 所有建模步骤成功完成！")
    return True






