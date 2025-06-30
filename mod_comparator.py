import json
import traceback
import sys
from pathlib import Path

def validate_file_path(file_path: Path, file_type: str) -> None:
    """验证文件路径是否存在且可读"""
    print(f"🔍 检查{file_type}文件路径: {file_path}")
    
    if not file_path.exists():
        raise FileNotFoundError(f"{file_type}文件不存在: {file_path}")
    
    if not file_path.is_file():
        raise NotADirectoryError(f"{file_type}路径不是文件: {file_path}")
    
    try:
        with open(file_path, 'r') as f:
            pass
    except PermissionError:
        raise PermissionError(f"没有权限读取{file_type}文件: {file_path}")
    
    print(f"✅ {file_type}文件路径有效")

def load_mods(file_path: Path) -> dict:
    """加载模组列表文件并返回模组ID到版本的映射"""
    print(f"📖 正在加载模组列表: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read(1024)  # 读取前1024字节用于格式验证
            if not content.strip().startswith('['):
                raise ValueError("模组列表文件格式错误，应为JSON数组")
            
            # 重置文件指针
            f.seek(0)
            mod_data = json.load(f)
            
            # 验证数据结构
            if not isinstance(mod_data, list):
                raise ValueError("模组列表内容不是有效的JSON数组")
            
            if not all('modid' in mod and 'version' in mod for mod in mod_data):
                missing = [i for i, mod in enumerate(mod_data) if 'modid' not in mod or 'version' not in mod]
                raise KeyError(f"模组列表中第{missing}项缺少'modid'或'version'字段")
            
            mod_map = {mod['modid']: mod['version'] for mod in mod_data}
            print(f"✅ 成功加载{len(mod_map)}个模组信息")
            return mod_map
    
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析错误: {e}")
        raise
    
    except Exception as e:
        print(f"❌ 加载模组列表时发生未知错误: {e}")
        raise

def compare_mods(client_mods: dict, server_mods: dict) -> dict:
    """比较客户端和服务端模组列表"""
    print("🔄 正在比较模组版本...")
    
    results = {
        "common_same_version": {},
        "common_diff_version": {},
        "client_only": [],
        "server_only": []
    }
    
    # 查找共同模组
    common_mods = set(client_mods.keys()) & set(server_mods.keys())
    
    for mod_id in common_mods:
        client_ver = client_mods[mod_id]
        server_ver = server_mods[mod_id]
        
        if client_ver == server_ver:
            results["common_same_version"][mod_id] = client_ver
        else:
            results["common_diff_version"][mod_id] = {
                "client": client_ver,
                "server": server_ver
            }
    
    # 查找仅存在于一方的模组
    results["client_only"] = list(set(client_mods.keys()) - common_mods)
    results["server_only"] = list(set(server_mods.keys()) - common_mods)
    
    print(f"✅ 比较完成")
    return results

def print_results(results: dict) -> None:
    """格式化输出比较结果"""
    print("\n" + "="*50)
    print(f"📊 模组比较结果")
    print("="*50)
    
    print(f"🔵 共同模组 (版本相同): {len(results['common_same_version'])}")
    if results['common_same_version']:
        print("\n".join(f"  - {mod}: {ver}" for mod, ver in results['common_same_version'].items()))
    
    print(f"\n🔴 共同模组 (版本不同): {len(results['common_diff_version'])}")
    if results['common_diff_version']:
        print("\n".join(f"  - {mod}: 客户端 {info['client']} vs 服务端 {info['server']}" 
                      for mod, info in results['common_diff_version'].items()))
    
    print(f"\n🟢 仅客户端存在的模组: {len(results['client_only'])}")
    if results['client_only']:
        print("\n".join(f"  - {mod}" for mod in results['client_only']))
    
    print(f"\n🟡 仅服务端存在的模组: {len(results['server_only'])}")
    if results['server_only']:
        print("\n".join(f"  - {mod}" for mod in results['server_only']))
    
    print("\n" + "="*50)

def main():
    print("\n" + "="*50)
    print("🔍 Minecraft 模组比较工具")
    print("="*50)
    
    # 定义文件路径
    client_file = Path("client/mods_client.json")
    server_file = Path("server/mod_server.json")
    
    try:
        # 验证文件路径
        validate_file_path(client_file, "客户端模组")
        validate_file_path(server_file, "服务端模组")
        
        # 加载模组列表
        client_mods = load_mods(client_file)
        server_mods = load_mods(server_file)
        
        if not client_mods or not server_mods:
            raise ValueError("模组列表为空，无法进行比较")
        
        # 比较模组
        results = compare_mods(client_mods, server_mods)
        
        # 输出结果
        print_results(results)
        
        print("\n✅ 比较完成！")
    
    except Exception as e:
        print("\n" + "!"*50)
        print(f"❌ 程序异常退出: {str(e)}")
        print("!"*50)
        
        # 保存详细错误日志
        with open("mod_comparator_error.log", "w", encoding="utf-8") as f:
            f.write(f"错误信息: {str(e)}\n\n")
            f.write("完整错误堆栈:\n")
            f.write(traceback.format_exc())
        
        print("\n📄 详细错误信息已保存到 mod_comparator_error.log")
    
    finally:
        # 防止闪退，等待用户输入
        input("\n按回车键退出...")

if __name__ == "__main__":
    main()