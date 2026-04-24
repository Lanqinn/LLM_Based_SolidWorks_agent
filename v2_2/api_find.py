# import win32com.client

# # 使用 EnsureDispatch 而不是 Dispatch
# # 这会自动查找 SolidWorks 的类型库，生成 python 接口文件（包含所有常量！）
# # ⚠️ 注意：第一次运行可能需要几秒钟
# swApp = win32com.client.gencache.EnsureDispatch("SldWorks.Application")

# # 打印一下常量看看
# import win32com.client.constants as const

# try:
#     print(f"swFmLPattern 的值是: {const.swFmLPattern}")  # 应该输出 22
#     print(f"swMbInformation 的值是: {const.swMbInformation}")
# except AttributeError:
#     print("⚠️ 没找到常量，可能是缓存未生成或生成失败。")






# 列出电脑里所有注册的 COM 组件,选择相关的组件会生成一个很大的文件，一般是官方的API,
from win32com.client import makepy
# 这会弹出一个窗口，列出电脑里所有注册的 COM 组件
makepy.main()