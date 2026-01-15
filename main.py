"""主程序入口"""
import signal
import sys
from config import Config
from scheduler import Scheduler


def signal_handler(sig, frame):
    """处理退出信号"""
    print("\n收到退出信号，正在关闭...")
    if scheduler:
        scheduler.stop()
    sys.exit(0)


if __name__ == "__main__":
    # 验证配置
    if not Config.validate():
        print("请检查配置文件中必要的API密钥是否已设置")
        print("请参考 .env.example 文件配置 .env 文件")
        sys.exit(1)
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 创建并启动调度器
    scheduler = Scheduler()
    scheduler.start(run_immediately=True)
    
    print("\n白银投资信息源AI工具已启动")
    print("按 Ctrl+C 退出程序\n")
    
    # 保持程序运行
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None, None)
