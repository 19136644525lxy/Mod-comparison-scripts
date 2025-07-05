import json
import traceback
import sys
import time
from pathlib import Path
import requests
from urllib.parse import quote
from colorama import init, Fore, Style

# -*- coding: utf-8 -*-

# 初始化颜色支持
init(autoreset=True)

# API配置
CURSEFORGE_API_KEY = "YOUR_API_KEY"  # 替换为您的CurseForge API密钥
CURSEFORGE_API_BASE_URL = "https://api.curseforge.com/v1"
MODRINTH_API_BASE_URL = "https://api.modrinth.com/v2"

# 美化配置
LOGO = r"""
    __  __  ______  ______   ______  ______  __  __  ______  ______  
   /\ \/ / /\  __ \/\  ___\ /\  ___\/\  __ \/\ \/\ \/\  __ \/\  ___\ 
   \ \  _"_ \ \ \/\ \ \  __\ \ \  __\ \ \/\ \ \ \_\ \ \ \/\ \ \  __\ 
    \ \_\ \_\ \_____\ \_____\ \ \_____\ \_____\ \_____\ \_____\ \_____\
     \/_/\/_/\/_____/\/_____/  \/_____/\/_____/\/_____/\/_____/\/_____/
"""

class ModComparator:
    def __init__(self):
        self.client_mods = {}
        self.server_mods = {}
        self.results = {}
        self.platforms = {
            "curseforge": {"enabled": bool(CURSEFORGE_API_KEY and CURSEFORGE_API_KEY != "YOUR_API_KEY"), "name": "CurseForge"},
            "modrinth": {"enabled": True, "name": "Modrinth"}
        }
    
    def print_header(self):
        """打印美化后的标题"""
        print(Fore.CYAN + Style.BRIGHT + LOGO)
        print(Fore.CYAN + Style.BRIGHT + "="*60)
        print(Fore.CYAN + Style.BRIGHT + "      Minecraft 模组比较工具 (双平台版)")
        print(Fore.CYAN + Style.BRIGHT + "="*60)
        print(f"{Fore.YELLOW}支持平台: " + ", ".join(
            f"{Fore.GREEN if p['enabled'] else Fore.RED}{p['name']}" 
            for p in self.platforms.values()
        ))
        print(Fore.CYAN + Style.BRIGHT + "="*60 + "\n")
    
    def confirm_start(self) -> bool:
        """确认是否开始比较"""
        print(f"{Fore.YELLOW}⚠️ 开始前请确认:")
        print(f"  1. 客户端模组列表已保存到 {Fore.CYAN}client/mods_client.json")
        print(f"  2. 服务端模组列表已保存到 {Fore.CYAN}server/mod_server.json")
        print(f"\n{Fore.BLUE}[按任意键开始 / Ctrl+C 退出]")
        
        try:
            input()  # 等待用户输入
            return True
        except KeyboardInterrupt:
            print(f"\n{Fore.RED}操作已取消")
            return False
    
    def validate_file_path(self, file_path: Path, file_type: str) -> None:
        """验证文件路径是否存在且可读"""
        print(f"{Fore.BLUE}🔍 检查{file_type}文件路径: {file_path}")
        
        if not file_path.exists():
            raise FileNotFoundError(f"{Fore.RED}{file_type}文件不存在: {file_path}")
        
        if not file_path.is_file():
            raise NotADirectoryError(f"{Fore.RED}{file_type}路径不是文件: {file_path}")
        
        try:
            with open(file_path, 'r') as f:
                pass
        except PermissionError:
            raise PermissionError(f"{Fore.RED}没有权限读取{file_type}文件: {file_path}")
        
        print(f"{Fore.GREEN}✅ {file_type}文件路径有效")
    
    def load_mods(self, file_path: Path) -> dict:
        """加载模组列表文件并返回模组ID到版本的映射"""
        print(f"{Fore.BLUE}📖 正在加载模组列表: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read(1024)  # 读取前1024字节用于格式验证
                if not content.strip().startswith('['):
                    raise ValueError(f"{Fore.RED}模组列表文件格式错误，应为JSON数组")
                
                # 重置文件指针
                f.seek(0)
                mod_data = json.load(f)
                
                # 验证数据结构
                if not isinstance(mod_data, list):
                    raise ValueError(f"{Fore.RED}模组列表内容不是有效的JSON数组")
                
                if not all('modid' in mod and 'version' in mod for mod in mod_data):
                    missing = [i for i, mod in enumerate(mod_data) if 'modid' not in mod or 'version' not in mod]
                    raise KeyError(f"{Fore.RED}模组列表中第{missing}项缺少'modid'或'version'字段")
                
                mod_map = {mod['modid']: mod['version'] for mod in mod_data}
                print(f"{Fore.GREEN}✅ 成功加载{len(mod_map)}个模组信息")
                return mod_map
        
        except json.JSONDecodeError as e:
            print(f"{Fore.RED}❌ JSON解析错误: {e}")
            raise
        
        except Exception as e:
            print(f"{Fore.RED}❌ 加载模组列表时发生未知错误: {e}")
            raise
    
    def compare_mods(self) -> dict:
        """比较客户端和服务端模组列表"""
        print(f"{Fore.BLUE}🔄 正在比较模组版本...")
        
        results = {
            "common_same_version": {},
            "common_diff_version": {},
            "client_only": [],
            "server_only": []
        }
        
        # 查找共同模组
        common_mods = set(self.client_mods.keys()) & set(self.server_mods.keys())
        
        for mod_id in common_mods:
            client_ver = self.client_mods[mod_id]
            server_ver = self.server_mods[mod_id]
            
            if client_ver == server_ver:
                results["common_same_version"][mod_id] = client_ver
            else:
                results["common_diff_version"][mod_id] = {
                    "client": client_ver,
                    "server": server_ver
                }
        
        # 查找仅存在于一方的模组
        results["client_only"] = list(set(self.client_mods.keys()) - common_mods)
        results["server_only"] = list(set(self.server_mods.keys()) - common_mods)
        
        print(f"{Fore.GREEN}✅ 比较完成")
        return results
    
    def search_curseforge(self, mod_id: str) -> dict:
        """在CurseForge上搜索模组"""
        if not self.platforms["curseforge"]["enabled"]:
            return {}
            
        try:
            headers = {"x-api-key": CURSEFORGE_API_KEY}
            url = f"{CURSEFORGE_API_BASE_URL}/mods/search?gameId=432&searchFilter={quote(mod_id)}"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            if data.get("data"):
                return data["data"][0]
            return {}
        except requests.RequestException as e:
            print(f"{Fore.RED}❌ CurseForge搜索失败: {e}")
            return {}
    
    def search_modrinth(self, mod_id: str) -> dict:
        """在Modrinth上搜索模组"""
        try:
            url = f"{MODRINTH_API_BASE_URL}/search?query={quote(mod_id)}&limit=1"
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            if data.get("hits"):
                return data["hits"][0]
            return {}
        except requests.RequestException as e:
            print(f"{Fore.RED}❌ Modrinth搜索失败: {e}")
            return {}
    
    def get_mod_info(self, mod_id: str) -> dict:
        """从所有可用平台获取模组信息"""
        info = {}
        
        # 优先搜索CurseForge
        if self.platforms["curseforge"]["enabled"]:
            info["curseforge"] = self.search_curseforge(mod_id)
            if info["curseforge"]:
                return info
        
        # 其次搜索Modrinth
        info["modrinth"] = self.search_modrinth(mod_id)
        return info
    
    def format_mod_info(self, mod_id: str, mod_info: dict) -> str:
        """格式化模组信息显示"""
        if not mod_info or (not mod_info.get("curseforge") and not mod_info.get("modrinth")):
            return f"{Fore.CYAN}{mod_id}{Fore.RESET} (无平台信息)"
        
        # 优先使用CurseForge信息
        if "curseforge" in mod_info and mod_info["curseforge"]:
            cf = mod_info["curseforge"]
            return f"{Fore.CYAN}{mod_id}{Fore.RESET} (名称: {cf['name']}, 描述: {cf['summary'][:50]}..., 平台: {Fore.YELLOW}CurseForge{Fore.RESET})"
        
        # 其次使用Modrinth信息
        elif "modrinth" in mod_info and mod_info["modrinth"]:
            mr = mod_info["modrinth"]
            return f"{Fore.CYAN}{mod_id}{Fore.RESET} (名称: {mr['title']}, 描述: {mr['description'][:50]}..., 平台: {Fore.YELLOW}Modrinth{Fore.RESET})"
        
        return f"{mod_id} (信息获取失败)"
    
    def print_results(self) -> None:
        """格式化输出比较结果"""
        print("\n" + Fore.CYAN + Style.BRIGHT + "="*60)
        print(f"{Fore.CYAN + Style.BRIGHT}📊 模组比较结果")
        print(Fore.CYAN + Style.BRIGHT + "="*60)
        
        print(f"{Fore.GREEN}🔵 共同模组 (版本相同): {len(self.results['common_same_version'])}")
        for mod, ver in self.results['common_same_version'].items():
            mod_info = self.get_mod_info(mod)
            print(f"  - {self.format_mod_info(mod, mod_info)} (版本: {Fore.BLUE}{ver}{Fore.RESET})")
        
        print(f"\n{Fore.RED}🔴 共同模组 (版本不同): {len(self.results['common_diff_version'])}")
        for mod, info in self.results['common_diff_version'].items():
            mod_info = self.get_mod_info(mod)
            print(f"  - {self.format_mod_info(mod, mod_info)} "
                  f"(客户端 {Fore.RED}{info['client']}{Fore.RESET} vs 服务端 {Fore.RED}{info['server']}{Fore.RESET})")
        
        print(f"\n{Fore.GREEN}🟢 仅客户端存在的模组: {len(self.results['client_only'])}")
        for mod in self.results['client_only']:
            mod_info = self.get_mod_info(mod)
            print(f"  - {self.format_mod_info(mod, mod_info)} (版本: {Fore.BLUE}{self.client_mods.get(mod)}{Fore.RESET})")
        
        print(f"\n{Fore.YELLOW}🟡 仅服务端存在的模组: {len(self.results['server_only'])}")
        for mod in self.results['server_only']:
            mod_info = self.get_mod_info(mod)
            print(f"  - {self.format_mod_info(mod, mod_info)} (版本: {Fore.BLUE}{self.server_mods.get(mod)}{Fore.RESET})")
        
        print("\n" + Fore.CYAN + Style.BRIGHT + "="*60)
        if not self.platforms["curseforge"]["enabled"]:
            print(f"{Fore.YELLOW}💡 提示: 设置CurseForge API密钥可获取更详细的模组信息")
    
    def run(self):
        """运行模组比较工具"""
        try:
            self.print_header()
            
            if not self.confirm_start():
                return
            
            # 定义文件路径
            client_file = Path("client/mods_client.json")
            server_file = Path("server/mod_server.json")
            
            # 验证文件路径
            self.validate_file_path(client_file, "客户端模组")
            self.validate_file_path(server_file, "服务端模组")
            
            # 加载模组列表
            self.client_mods = self.load_mods(client_file)
            self.server_mods = self.load_mods(server_file)
            
            if not self.client_mods or not self.server_mods:
                raise ValueError(f"{Fore.RED}模组列表为空，无法进行比较")
            
            # 比较模组
            self.results = self.compare_mods()
            
            # 输出结果
            self.print_results()
            
            print(f"\n{Fore.GREEN}✅ 比较完成！")
        
        except Exception as e:
            print("\n" + Fore.RED + Style.BRIGHT + "!"*60)
            print(f"{Fore.RED}❌ 程序异常退出: {str(e)}")
            print(Fore.RED + Style.BRIGHT + "!"*60)
            
            # 保存详细错误日志
            with open("mod_comparator_error.log", "w", encoding="utf-8") as f:
                f.write(f"错误信息: {str(e)}\n\n")
                f.write("完整错误堆栈:\n")
                f.write(traceback.format_exc())
            
            print(f"\n{Fore.YELLOW}📄 详细错误信息已保存到 mod_comparator_error.log")
        
        finally:
            # 防止闪退，等待用户输入
            print(f"\n{Fore.BLUE}[按任意键退出]")
            input()

if __name__ == "__main__":
    comparator = ModComparator()
    comparator.run()    