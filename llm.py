
'''常量访问测试'''


from openai import OpenAI
import json  
# --- 1. 配置和客户端初始化 ---
client = OpenAI(api_key="sk-hhdlfuwibkcceysdqnszndquuyhuoaavvrdtnzqltttejdnt", 
                base_url="https://api.siliconflow.cn/v1")

'''示例'''
response = client.chat.completions.create(
        model="Pro/zai-org/GLM-4.7",   # zai-org/GLM-4.6  Qwen/Qwen3-235B-A22B   Qwen/Qwen3-Coder-480B-A35B-Instruct
        messages=[
            {"role": "system", "content": "You are a helpful assistant designed to output JSON."},
            {"role": "user", "content": "? 2020 年世界奥运会乒乓球男子和女子单打冠军分别是谁? "
             "Please respond in the format {\"男子冠军\": ..., \"女子冠军\": ...}"}
        ],
        response_format={"type": "json_object"}
    )

print(response.choices[0].message.content)


# from openai import OpenAI

# client = OpenAI(
#     api_key="515910d5fc3d4b219dca5e1955bcfbc0.BBS7k22L6svnfjEP",
#     base_url="https://open.bigmodel.cn/api/paas/v4/"
# )

# completion = client.chat.completions.create(
#     model="glm-4.7",
#     messages=[
#             {"role": "system", "content": "You are a helpful assistant designed to output JSON."},
#             {"role": "user", "content": "? 2020 年世界奥运会乒乓球男子和女子单打冠军分别是谁? "
#              "Please respond in the format {\"男子冠军\": ..., \"女子冠军\": ...}"}
#         ],
#         response_format={"type": "json_object"},
#     top_p=0.7,
#     temperature=0.9
# )

# print(completion.choices[0].message.content)



