import json
import traceback
import sys
import time
from pathlib import Path
import requests
from urllib.parse import quote
from colorama import init, Fore, Style
from tabulate import tabulate 

# -*- coding: utf-8 -*-

# 初始化颜色支持
init(autoreset=True)

# API配置
CURSEFORGE_API_KEY = "YOUR_API_KEY"  # 替换为您的CurseForge API密钥
CURSEFORGE_API_BASE_URL = "https://api.curseforge.com/v1"
MODRINTH_API_BASE_URL = "https://api.modrinth.com/v2"

# 美化配置 - 新LOGO与作者信息
LOGO = r"""
    __     __  ______  ______   ______  ______  __    __  ______   ______  
   /\ \  _ \ \/\  __ \/\  ___\ /\  ___\/\  __ \/\ "-./  \/\  __ \ /\  ___\ 
   \ \ \/ ".\ \ \ \/\ \ \  __\ \ \  __\ \ \/\ \ \ \-./\ \ \ \/\ \ \ \  __\ 
    \ \__/".~\_\ \_____\ \_____\ \ \_____\ \_____\ \_\ \ \_\ \_____\_\ \_____\
     \/_/   \/_/\/_____/\/_____/  \/_____/\/_____/\/_/  \/_/\/_____/_/\/_____/
                                                                            
                        作者: 奕暃 | Minecraft 整合包模组列表比较工具
"""

# 加载动画字符
LOADING_FRAMES = ["|", "/", "-", "\\"]

class ModComparator:
    def __init__(self):
        self.client_mods = {}
        self.server_mods = {}
        self.results = {}
        self.platforms = {
            "curseforge": {"enabled": bool(CURSEFORGE_API_KEY and CURSEFORGE_API_KEY != "YOUR_API_KEY"), "name": "CurseForge"},
            "modrinth": {"enabled": True, "name": "Modrinth"}
        }
        self.start_time = 0
    
    def print_header(self):
        """打印美化后的标题与作者信息"""
        print(Fore.CYAN + Style.BRIGHT + LOGO)
        print(Fore.CYAN + Style.BRIGHT + "="*70)
        print(Fore.CYAN + Style.BRIGHT + "          Minecraft 模组列表比较工具 (双平台增强版)")
        print(Fore.CYAN + Style.BRIGHT + "="*70)
        print(f"{Fore.YELLOW}支持平台: " + ", ".join(
            f"{Fore.GREEN if p['enabled'] else Fore.RED}{p['name']}" 
            for p in self.platforms.values()
        ))
        print(Fore.CYAN + Style.BRIGHT + "="*70 + "\n")
    
    def animate_loading(self, message: str, duration: float = 0.1):
        """显示加载动画"""
        frame_index = 0
        while True:
            frame = LOADING_FRAMES[frame_index % len(LOADING_FRAMES)]
            sys.stdout.write(f"\r{Fore.YELLOW}⏳ {message} {frame}")
            sys.stdout.flush()
            frame_index += 1
            time.sleep(duration)
            if time.time() - self.start_time > 10:  # 最长显示10秒
                break
    
    def stop_loading(self, success: bool = True, message: str = ""):
        """停止加载动画并显示结果"""
        sys.stdout.write("\r" + " " * 60 + "\r")  # 清除加载行
        if success:
            print(f"{Fore.GREEN}✅ {message}")
        else:
            print(f"{Fore.RED}❌ {message}")
    
    def confirm_start(self) -> bool:
        """确认是否开始比较，增加交互美化"""
        print(f"{Fore.YELLOW}⚠️ 开始前请确认:")
        print(f"  1. 客户端模组列表已保存到 {Fore.CYAN}client/mods_client.json")
        print(f"  2. 服务端模组列表已保存到 {Fore.CYAN}server/mod_server.json")
        print(f"\n{Fore.BLUE}[按 Enter 开始比较 / Ctrl+C 退出]")
        
        try:
            input()
            return True
        except KeyboardInterrupt:
            print(f"\n{Fore.RED}操作已取消")
            return False
    
    def validate_file_path(self, file_path: Path, file_type: str) -> None:
        """验证文件路径，增加加载动画"""
        self.start_time = time.time()
        loading_thread = threading.Thread(target=self.animate_loading, args=(f"检查{file_type}文件路径",))
        loading_thread.daemon = True
        loading_thread.start()
        
        try:
            if not file_path.exists():
                raise FileNotFoundError(f"{file_type}文件不存在: {file_path}")
            
            if not file_path.is_file():
                raise NotADirectoryError(f"{file_type}路径不是文件: {file_path}")
            
            with open(file_path, 'r') as f:
                pass  # 仅验证可读性
            
            self.stop_loading(True, f"{file_type}文件路径有效: {file_path}")
        
        except Exception as e:
            self.stop_loading(False, f"{file_type}文件验证失败: {str(e)}")
            raise
    
    def load_mods(self, file_path: Path) -> dict:
        """加载模组列表，增加加载动画和详细统计"""
        self.start_time = time.time()
        loading_thread = threading.Thread(target=self.animate_loading, args=(f"加载{file_path.name}中的模组信息",))
        loading_thread.daemon = True
        loading_thread.start()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read(1024)
                if not content.strip().startswith('['):
                    raise ValueError("文件格式错误，应为JSON数组")
                
                f.seek(0)
                mod_data = json.load(f)
                
                if not isinstance(mod_data, list):
                    raise ValueError("内容不是有效的JSON数组")
                
                valid_mods = [mod for mod in mod_data if 'modid' in mod and 'version' in mod]
                invalid_mods = len(mod_data) - len(valid_mods)
                
                mod_map = {mod['modid']: mod['version'] for mod in valid_mods}
                self.stop_loading(
                    True, 
                    f"成功加载 {len(mod_map)} 个模组 (跳过 {invalid_mods} 个无效条目) 来自 {file_path}"
                )
                return mod_map
        
        except Exception as e:
            self.stop_loading(False, f"加载模组失败: {str(e)}")
            raise
    
    def compare_mods(self) -> dict:
        """比较模组列表，增加进度提示"""
        self.start_time = time.time()
        loading_thread = threading.Thread(target=self.animate_loading, args=("正在比较客户端与服务端模组",))
        loading_thread.daemon = True
        loading_thread.start()
        
        results = {
            "common_same_version": {},
            "common_diff_version": {},
            "client_only": [],
            "server_only": []
        }
        
        # 计算共同模组
        common_mods = set(self.client_mods.keys()) & set(self.server_mods.keys())
        total_mods = len(self.client_mods) + len(self.server_mods)
        
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
        
        # 计算独有模组
        results["client_only"] = sorted(list(set(self.client_mods.keys()) - common_mods))
        results["server_only"] = sorted(list(set(self.server_mods.keys()) - common_mods))
        
        self.stop_loading(
            True, 
            f"比较完成 (共分析 {total_mods} 个模组，发现 {len(common_mods)} 个共同模组)"
        )
        return results
    
    def search_curseforge(self, mod_id: str) -> dict:
        """CurseForge搜索，优化错误提示"""
        if not self.platforms["curseforge"]["enabled"]:
            return {}
            
        try:
            headers = {"x-api-key": CURSEFORGE_API_KEY}
            url = f"{CURSEFORGE_API_BASE_URL}/mods/search?gameId=432&searchFilter={quote(mod_id)}"
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])[0] if data.get("data") else {}
        except Exception as e:
            return {}
    
    def search_modrinth(self, mod_id: str) -> dict:
        """Modrinth搜索，优化错误提示"""
        try:
            url = f"{MODRINTH_API_BASE_URL}/search?query={quote(mod_id)}&limit=1"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            return data.get("hits", [])[0] if data.get("hits") else {}
        except Exception as e:
            return {}
    
    def get_mod_info(self, mod_id: str) -> dict:
        """获取模组信息，增加超时控制"""
        info = {"name": mod_id}  # 默认使用mod_id作为名称
        
        # 并行搜索（模拟）
        cf_info = self.search_curseforge(mod_id)
        if cf_info:
            info.update({
                "name": cf_info.get("name", mod_id),
                "desc": cf_info.get("summary", "无描述"),
                "platform": "CurseForge",
                "url": cf_info.get("links", {}).get("websiteUrl", "")
            })
            return info
        
        mr_info = self.search_modrinth(mod_id)
        if mr_info:
            info.update({
                "name": mr_info.get("title", mod_id),
                "desc": mr_info.get("description", "无描述"),
                "platform": "Modrinth",
                "url": f"https://modrinth.com/mod/{mr_info.get('slug', '')}"
            })
            return info
        
        return info
    
    def print_results(self) -> None:
        """表格化展示结果，优化视觉层次"""
        print("\n" + Fore.CYAN + Style.BRIGHT + "="*70)
        print(f"{Fore.CYAN + Style.BRIGHT}📊 模组比较详细结果")
        print(Fore.CYAN + Style.BRIGHT + "="*70)
        
        # 1. 共同且版本相同的模组
        if self.results["common_same_version"]:
            print(f"\n{Fore.GREEN}🔵 共同模组 (版本相同) - {len(self.results['common_same_version'])} 个")
            print(Fore.GREEN + "-"*65)
            table_data = []
            for mod_id, ver in self.results["common_same_version"].items():
                mod_info = self.get_mod_info(mod_id)
                table_data.append([
                    f"{Fore.CYAN}{mod_info['name']}",
                    f"{Fore.WHITE}{mod_id}",
                    f"{Fore.BLUE}{ver}",
                    f"{Fore.YELLOW}{mod_info['platform'] if 'platform' in mod_info else '未知'}"
                ])
            print(tabulate(
                table_data,
                headers=[f"{Fore.CYAN}模组名称", f"{Fore.CYAN}Mod ID", f"{Fore.CYAN}版本", f"{Fore.CYAN}来源"],
                tablefmt="grid"
            ))
        
        # 2. 共同但版本不同的模组
        if self.results["common_diff_version"]:
            print(f"\n{Fore.RED}🔴 共同模组 (版本不同) - {len(self.results['common_diff_version'])} 个")
            print(Fore.RED + "-"*65)
            table_data = []
            for mod_id, info in self.results["common_diff_version"].items():
                mod_info = self.get_mod_info(mod_id)
                table_data.append([
                    f"{Fore.CYAN}{mod_info['name']}",
                    f"{Fore.WHITE}{mod_id}",
                    f"{Fore.RED}{info['client']}",
                    f"{Fore.RED}{info['server']}"
                ])
            print(tabulate(
                table_data,
                headers=[f"{Fore.CYAN}模组名称", f"{Fore.CYAN}Mod ID", f"{Fore.CYAN}客户端版本", f"{Fore.CYAN}服务端版本"],
                tablefmt="grid"
            ))
        
        # 3. 仅客户端有的模组
        if self.results["client_only"]:
            print(f"\n{Fore.GREEN}🟢 仅客户端存在的模组 - {len(self.results['client_only'])} 个")
            print(Fore.GREEN + "-"*65)
            table_data = []
            for mod_id in self.results["client_only"]:
                mod_info = self.get_mod_info(mod_id)
                table_data.append([
                    f"{Fore.CYAN}{mod_info['name']}",
                    f"{Fore.WHITE}{mod_id}",
                    f"{Fore.BLUE}{self.client_mods[mod_id]}"
                ])
            print(tabulate(
                table_data,
                headers=[f"{Fore.CYAN}模组名称", f"{Fore.CYAN}Mod ID", f"{Fore.CYAN}客户端版本"],
                tablefmt="grid"
            ))
        
        # 4. 仅服务端有的模组
        if self.results["server_only"]:
            print(f"\n{Fore.YELLOW}🟡 仅服务端存在的模组 - {len(self.results['server_only'])} 个")
            print(Fore.YELLOW + "-"*65)
            table_data = []
            for mod_id in self.results["server_only"]:
                mod_info = self.get_mod_info(mod_id)
                table_data.append([
                    f"{Fore.CYAN}{mod_info['name']}",
                    f"{Fore.WHITE}{mod_id}",
                    f"{Fore.BLUE}{self.server_mods[mod_id]}"
                ])
            print(tabulate(
                table_data,
                headers=[f"{Fore.CYAN}模组名称", f"{Fore.CYAN}Mod ID", f"{Fore.CYAN}服务端版本"],
                tablefmt="grid"
            ))
        
        # 总结信息
        print("\n" + Fore.CYAN + Style.BRIGHT + "="*70)
        print(f"{Fore.YELLOW}📝 总结:")
        print(f"  - 客户端总模组: {Fore.CYAN}{len(self.client_mods)}")
        print(f"  - 服务端总模组: {Fore.CYAN}{len(self.server_mods)}")
        print(f"  - 共同模组: {Fore.CYAN}{len(self.results['common_same_version']) + len(self.results['common_diff_version'])}")
        print(f"  - 版本不一致: {Fore.RED}{len(self.results['common_diff_version'])}")
        if not self.platforms["curseforge"]["enabled"]:
            print(f"\n{Fore.YELLOW}💡 提示: 配置CurseForge API密钥可获取更完整的模组信息")
        print(Fore.CYAN + Style.BRIGHT + "="*70)
    
    def run(self):
        """主运行函数，增加时间统计"""
        try:
            start_total = time.time()
            self.print_header()
            
            if not self.confirm_start():
                return
            
            # 定义文件路径
            client_file = Path("client/mods_client.json")
            server_file = Path("server/mod_server.json")
            
            # 验证文件
            self.validate_file_path(client_file, "客户端模组")
            self.validate_file_path(server_file, "服务端模组")
            
            # 加载模组
            self.client_mods = self.load_mods(client_file)
            self.server_mods = self.load_mods(server_file)
            
            if not self.client_mods or not self.server_mods:
                raise ValueError("客户端或服务端模组列表为空，无法比较")
            
            # 比较模组
            self.results = self.compare_mods()
            
            # 输出结果
            self.print_results()
            
            # 统计总耗时
            total_time = round(time.time() - start_total, 2)
            print(f"\n{Fore.GREEN}✅ 所有操作完成！总耗时: {total_time} 秒")
        
        except Exception as e:
            print("\n" + Fore.RED + Style.BRIGHT + "!"*70)
            print(f"{Fore.RED}❌ 程序异常退出: {str(e)}")
            print(Fore.RED + Style.BRIGHT + "!"*70)
            
            # 保存错误日志
            with open("mod_comparator_error.log", "w", encoding="utf-8") as f:
                f.write(f"错误时间: {time.ctime()}\n")
                f.write(f"错误信息: {str(e)}\n\n")
                f.write("错误堆栈:\n")
                f.write(traceback.format_exc())
            
            print(f"\n{Fore.YELLOW}📄 详细错误已保存到 mod_comparator_error.log")
        
        finally:
            print(f"\n{Fore.BLUE}感谢使用 奕暃 开发的模组比较工具 | 按任意键退出")
            input()

if __name__ == "__main__":
    import threading  # 延迟导入以避免未使用的情况
    comparator = ModComparator()
    comparator.run()