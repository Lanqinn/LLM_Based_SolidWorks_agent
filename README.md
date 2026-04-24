# LLM_Based_SolidWorks_agent
LLM-Based Intelligent Agent for Automated SolidWorks Modeling基于大语言模型的 SolidWorks 自动化智能建模助手

    这是一个通过自然语言输入进行简单自动3D建模的智能体，通过LLM控制SolidWorks进行3D零件生成。可应用于机械设计，也可作为智能体开发的入门项目。
本项目开发了一个基于大语言模型（LLM）的智能体，能够解析用户的自然语言指令，通过 Python API 自动驱动 SolidWorks 完成复杂的 3D 建模任务。它不仅能理解“画个正方体”这种简单指令，还能处理“在顶面中心打一个直径10mm的穿透孔”等涉及空间几何关系的组合逻辑。

核心技术亮点 (Key Features)
  多步逻辑规划 (Structured Multi-step Planning):
  利用 LLM 的推理能力，将模糊的用户需求（如“建个桌子”）拆解为“创建草图 -> 绘制矩形 -> 拉伸 -> 选面 -> 阵列”等原子化指令序列。
  
  几何感知选面系统 (Geometry-Aware Face Selection):
  在 lib.py 中实现了基于空间坐标和法向量的选面逻辑，解决了自动化建模中“如何准确选中目标平面”的行业痛点。
  
  鲁棒的调度执行器 (Robust Instruction Dispatcher):
  llm_connector.py 具备参数自动校验与清洗功能（Auto-cleaning），能有效拦截 LLM 生成的非法参数，确保 SolidWorks API 调用的稳定性。
  
  多模型适配 (Multi-LLM Backend Support):
  内置对 GLM-4、Qwen、DeepSeek 等主流模型的适配，并在 agent.py 中针对建模逻辑准确度进行了深度调优。

文件描述
  1、环境配置
  详见文件夹：“环境配置指南”，包含两部分：（1）environment.yaml文件，说明了python环境；（2）环境配置.docx，说明了SolidWorks版本（后续简称SW），和一些其他的简要说明。
  
  2、运行
  源文件在“v2_2”里，主要是3个程序：（1）agent.py是主程序，直接运行即可；（2）lib.py是封装的SW底层API函数，也就是大模型调用的tools，给出了一些常见拉伸、切除等函数的输入输出，和简要的功能描述;
  （3）llm_connector.py，是调度器，主要是负责和大模型通信，解析大模型的输出，将其转化为有效的、可执行的命令。
  
  3、示例
  在文件夹：“宣传”中，是一些基本的演示示例，视频文件，展示了一些基本功能的实现，包括基本的拉伸切除、旋转生成、文字拉伸、外观渲染等功能。
  
  该智能体使用的大模型API来源于硅基流动（https://siliconflow.cn/，具体使用流程参考官方网站），其中对于中国的各个大语言模型，智普清言的模型效果最好，GLM4.7,GLM4.6等。


**该项目运行流程：**
  （1）把整个项目下载，
  （2）并配置好python环境和安装好合适版本的SW，
  （3）填写你的大模型APL KEY(我用的是硅基流动，在llm_connector.py里修改)，以及修改文件保存的路径（在agent.py里修改）。
  （4）还要设置好你的SW模板的路径（一般是：template_path = rf"C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2024\templates\gb_part.prtdot"），（在agent.py里修改）
  （5）运行主程序agent.py，就可以发现该智能体会自动打开你的SW，进行建模。


其他文件说明：
关键内容记录.docx: 是关于SW底层API文件（各个功能函数）的详细说明，当你需要扩展给智能体添加新tools的时候，可以来这里查。SW_2024_type_library.py就是按照说明生成的底层API文件，没必要看，很繁杂。
功能说明.docx：是关于该版本智能体具备的具体功能描述。
所有的.SLDPRT均为生成的模型文件。




