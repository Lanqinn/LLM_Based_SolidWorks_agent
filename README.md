# LLM_Based_SolidWorks_agent
LLM-Based Intelligent Agent for Automated SolidWorks Modeling

这是一个通过自然语言输入进行简单自动3D建模的智能体，通过LLM控制SolidWorks进行3D零件生成。可应用于机械设计，也可作为智能体开发的入门项目。

1、环境配置
详见文件夹：环境配置指南，包含两部分：（1）python环境，environment.yaml文件；（2）SolidWorks版本，和一些简要说明。

2、运行
源文件在v2_2里，主要是3个程序：（1）agent.py是主程序，直接运行即可；（2）lib.py是封装的SW底层API函数，也就是大模型调用的tools，给出了一些常见拉伸、切除等函数的输入输出，和简要的功能描述;
（3）llm_connector.py，是调度器，主要是负责和大模型通信，解析大模型的输出，将其转化为有效的、可执行的命令。

3、示例
在文件夹：宣传中，是一些基本的演示示例，视频文件，展示了一些基本功能的实现，包括基本的拉伸切除、旋转生成、文字拉伸、外观渲染等功能。

该智能体使用的大模型API来源于硅基流动（https://siliconflow.cn/，具体使用流程参考官方网站），其中对于中国的各个大语言模型，智普清言的模型效果最好，GLM4.7,GLM4.6等。


