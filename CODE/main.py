"""
主程序入口
支持命令行参数和环境变量配置
"""
import argparse
import os
import sys
from pathlib import Path

from config import GlobalConfig, ReviewMode, LLMConfig, load_config_from_env
from batch_processor import BatchProcessor


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="企业合规文档批量分析工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 法规审查模式
  python main.py --mode regulation --input ./regulations --output ./results
  
  # 文档审查模式  
  python main.py --mode documentation --input ./documents --output ./results
  
  # 指定API密钥
  python main.py --deepseek-key YOUR_KEY --openai-key YOUR_KEY --anthropic-key YOUR_KEY
  
  # 指定模型
  python main.py --deepseek-model deepseek-chat --openai-model gpt-4 --anthropic-model claude-3-opus-20240229
        """
    )
    
    # 基本参数
    parser.add_argument(
        '--mode', 
        type=str, 
        choices=['regulation', 'documentation'],
        default='regulation',
        help='审查模式: regulation(法规审查) 或 documentation(文档审查)'
    )
    
    parser.add_argument(
        '--input', 
        type=str, 
        required=True,
        help='输入文件或目录路径'
    )
    
    parser.add_argument(
        '--output', 
        type=str, 
        default='./output_results',
        help='输出目录路径'
    )
    
    # API密钥参数
    parser.add_argument(
        '--deepseek-key', 
        type=str,
        help='DeepSeek API密钥'
    )
    
    parser.add_argument(
        '--openai-key', 
        type=str,
        help='OpenAI API密钥'
    )
    
    parser.add_argument(
        '--anthropic-key', 
        type=str,
        help='Anthropic API密钥'
    )
    
    # 模型选择参数
    parser.add_argument(
        '--deepseek-model', 
        type=str,
        default='deepseek-chat',
        help='DeepSeek模型名称'
    )
    
    parser.add_argument(
        '--openai-model', 
        type=str,
        default='gpt-4o-mini',
        help='OpenAI模型名称'
    )
    
    parser.add_argument(
        '--anthropic-model', 
        type=str,
        default='claude-3-5-sonnet-20241022',
        help='Anthropic模型名称'
    )
    
    # 其他参数
    parser.add_argument(
        '--categories-per-call', 
        type=int,
        default=2,
        help='每次API调用处理的类别数'
    )
    
    parser.add_argument(
        '--no-individual-results', 
        action='store_true',
        help='不保存各LLM的单独结果'
    )
    
    parser.add_argument(
        '--no-consolidated-results', 
        action='store_true',
        help='不保存合并结果'
    )
    
    return parser.parse_args()


def create_config_from_args(args) -> GlobalConfig:
    """从命令行参数创建配置"""
    # 先加载环境变量配置
    config = load_config_from_env()
    
    # 覆盖命令行参数
    config.review_mode = ReviewMode.REGULATION if args.mode == 'regulation' else ReviewMode.DOCUMENTATION
    config.input_path = args.input
    config.output_path = args.output
    config.categories_per_call = args.categories_per_call
    config.save_individual_results = not args.no_individual_results
    config.save_consolidated_results = not args.no_consolidated_results
    
    # 更新API密钥
    if args.deepseek_key:
        config.llm_configs['deepseek'].api_key = args.deepseek_key
    if args.openai_key:
        config.llm_configs['openai'].api_key = args.openai_key
    if args.anthropic_key:
        config.llm_configs['anthropic'].api_key = args.anthropic_key
    
    # 更新模型
    config.llm_configs['deepseek'].model = args.deepseek_model
    config.llm_configs['openai'].model = args.openai_model
    config.llm_configs['anthropic'].model = args.anthropic_model
    
    return config


def validate_config(config: GlobalConfig):
    """验证配置"""
    # 检查输入路径
    if not Path(config.input_path).exists():
        raise ValueError(f"输入路径不存在: {config.input_path}")
    
    # 检查是否至少有一个API密钥
    has_key = any(
        llm_config.api_key 
        for llm_config in config.llm_configs.values()
    )
    
    if not has_key:
        print("警告: 未配置任何API密钥")
        print("请通过以下方式之一提供API密钥:")
        print("1. 命令行参数: --deepseek-key, --openai-key, --anthropic-key")
        print("2. 环境变量: DEEPSEEK_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY")
        return False
    
    return True


def print_config(config: GlobalConfig):
    """打印配置信息"""
    print("=" * 80)
    print("配置信息")
    print("=" * 80)
    print(f"审查模式: {'法规审查' if config.review_mode == ReviewMode.REGULATION else '文档审查'}")
    print(f"输入路径: {config.input_path}")
    print(f"输出路径: {config.output_path}")
    print(f"每次处理类别数: {config.categories_per_call}")
    print("\nLLM配置:")
    
    for provider, llm_config in config.llm_configs.items():
        has_key = "已配置" if llm_config.api_key else "未配置"
        print(f"  {provider}: {llm_config.model} (API密钥: {has_key})")
    
    print("=" * 80)


def main():
    """主函数"""
    try:
        # 解析参数
        args = parse_arguments()
        
        # 创建配置
        config = create_config_from_args(args)
        
        # 验证配置
        if not validate_config(config):
            sys.exit(1)
        
        # 打印配置
        print_config(config)
        
        # 创建批处理器并执行
        processor = BatchProcessor(config)
        results = processor.process_all_files()
        
        if results:
            print(f"\n处理完成! 结果保存在: {processor.run_output_dir}")
        else:
            print("\n未找到需要处理的文件")
        
    except KeyboardInterrupt:
        print("\n\n处理被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n错误: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()