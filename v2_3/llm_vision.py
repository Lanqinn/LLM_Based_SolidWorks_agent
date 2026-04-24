from openai import OpenAI
import json  
import os
import base64

# --- 语言模型 ---

# client = OpenAI(api_key="sk-hhdlfuwibkcceysdqnszndquuyhuoaavvrdtnzqltttejdnt", 
#                 base_url="https://api.siliconflow.cn/v1")

# '''示例'''
# response = client.chat.completions.create(
#         model="Pro/zai-org/GLM-4.7",   # zai-org/GLM-4.6  Qwen/Qwen3-235B-A22B   Qwen/Qwen3-Coder-480B-A35B-Instruct
#         messages=[
#             {"role": "system", "content": "You are a helpful assistant designed to output JSON."},
#             {"role": "user", "content": "? 2020 年世界奥运会乒乓球男子和女子单打冠军分别是谁? "
#              "Please respond in the format {\"男子冠军\": ..., \"女子冠军\": ...}"}
#         ],
#         response_format={"type": "json_object"}
#     )

# print(response.choices[0].message.content)



# --- 视觉语言模型 ---

client = OpenAI(api_key="sk-hhdlfuwibkcceysdqnszndquuyhuoaavvrdtnzqltttejdnt", 
                base_url="https://api.siliconflow.cn/v1")

'''示例'''
# 2. 定义图片转 Base64 的函数 (核心步骤)
def encode_image(image_path):
    """
    读取本地图片并转换为 Base64 编码字符串
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"未找到文件: {image_path}")
        
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# 3. 设置参数
local_image_path = rf"C:\Users\Free\Desktop\SW宏\v2_3\test_image.png"  # 替换为你本地图片的路径
# 如果没有图片，请先放一张图片在同目录下，或者填写绝对路径
# 例如: r"C:\Users\Desktop\screenshot.jpg"

try:
    # 获取 Base64 编码
    base64_image = encode_image(local_image_path)

    # 4. 发送请求
    response = client.chat.completions.create(
        # --- 关键修改 A: 模型 ---
        # 硅基流动目前支持的视觉模型推荐：
        # "Qwen/Qwen2-VL-72B-Instruct" (性能最强)
        # "THUDM/glm-4v-9b" (智谱的视觉模型)
        # "Qwen/Qwen2-VL-7B-Instruct" (速度快)
        # zai-org/GLM-4.6V
        model="Qwen/Qwen2-VL-72B-Instruct", 
        
        messages=[
            {
                "role": "user",
                # --- 关键修改 B: 内容格式 ---
                "content": [
                    {
                        "type": "text",
                        "text": "请详细描述这张图片的内容，如果里面有文字，请提取出来。"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            # 必须加上 data:image/...;base64, 前缀
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        stream=False
    )

    # 5. 输出结果
    print("AI 回复内容:")
    print(response.choices[0].message.content)

except Exception as e:
    print(f"发生错误: {e}")