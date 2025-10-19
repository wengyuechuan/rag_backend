#!/usr/bin/env python3
"""
RAG 智能对话客户端
命令行交互式聊天界面
"""

import requests
import json
import sys
from typing import Optional

BASE_URL = "http://localhost:8000/api/v1"


class ChatClient:
    """聊天客户端"""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session_id: Optional[int] = None
        self.kb_id: Optional[int] = None
    
    def check_server(self) -> bool:
        """检查服务器是否可用"""
        try:
            response = requests.get(f"{self.base_url.replace('/api/v1', '')}/health", timeout=3)
            return response.status_code == 200
        except Exception:
            return False
    
    def list_knowledge_bases(self):
        """列出所有知识库"""
        try:
            response = requests.get(f"{self.base_url}/knowledge-bases")
            if response.status_code == 200:
                kbs = response.json()
                if not kbs:
                    print("❌ 没有可用的知识库，请先创建知识库")
                    return []
                
                print("\n📚 可用的知识库:")
                for kb in kbs:
                    print(f"  [{kb['id']}] {kb['name']}")
                    if kb.get('description'):
                        print(f"      {kb['description']}")
                    print(f"      文档数: {kb['document_count']}, 分块数: {kb['total_chunks']}")
                
                return kbs
            else:
                print(f"❌ 获取知识库失败: {response.text}")
                return []
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            return []
    
    def create_session(self, kb_id: int, use_vector: bool = True, use_graph: bool = True) -> bool:
        """创建会话"""
        try:
            response = requests.post(
                f"{self.base_url}/chat/sessions",
                json={
                    "knowledge_base_id": kb_id,
                    "title": "命令行对话",
                    "use_vector_search": use_vector,
                    "use_graph_search": use_graph,
                    "search_top_k": 5
                }
            )
            
            if response.status_code == 201:
                session = response.json()
                self.session_id = session['id']
                self.kb_id = kb_id
                print(f"\n✅ 会话创建成功 (ID: {self.session_id})")
                print(f"   向量搜索: {'✅' if use_vector else '❌'}")
                print(f"   图谱搜索: {'✅' if use_graph else '❌'}")
                return True
            else:
                print(f"❌ 创建会话失败: {response.text}")
                return False
        except Exception as e:
            print(f"❌ 创建会话失败: {e}")
            return False
    
    def send_message(self, message: str):
        """发送消息（流式）"""
        if not self.session_id:
            print("❌ 没有活动会话，请先创建会话")
            return
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                json={
                    "session_id": self.session_id,
                    "message": message,
                    "stream": True,
                    "temperature": 0.7
                },
                stream=True,
                timeout=60
            )
            
            if response.status_code != 200:
                print(f"❌ 发送失败: {response.text}")
                return
            
            print("🤖 AI: ", end='', flush=True)
            
            chunks_count = 0
            entities_count = 0
            
            for line in response.iter_lines():
                if line:
                    line_text = line.decode('utf-8')
                    if line_text.startswith('data: '):
                        try:
                            data = json.loads(line_text[6:])
                            
                            if data['type'] == 'context':
                                chunks_count = data['data']['chunks']
                                entities_count = data['data']['entities']
                                if chunks_count > 0 or entities_count > 0:
                                    print(f"[检索: {chunks_count}块, {entities_count}实体] ", end='', flush=True)
                            
                            elif data['type'] == 'chunk':
                                print(data['data'], end='', flush=True)
                            
                            elif data['type'] == 'done':
                                print(f"\n[耗时: {data['data']['processing_time']:.2f}秒]")
                            
                            elif data['type'] == 'error':
                                print(f"\n❌ 错误: {data['data']}")
                        
                        except json.JSONDecodeError:
                            pass
        
        except requests.exceptions.Timeout:
            print("\n⏱️  请求超时，请稍后重试")
        except Exception as e:
            print(f"\n❌ 发送失败: {e}")
    
    def show_history(self, limit: int = 10):
        """显示会话历史"""
        if not self.session_id:
            print("❌ 没有活动会话")
            return
        
        try:
            response = requests.get(
                f"{self.base_url}/chat/sessions/{self.session_id}/history",
                params={"limit": limit}
            )
            
            if response.status_code == 200:
                history = response.json()
                session = history['session']
                messages = history['messages']
                
                print(f"\n📜 会话历史")
                print(f"{'='*60}")
                print(f"会话 ID: {session['id']}")
                print(f"标题: {session['title']}")
                print(f"消息数: {session['message_count']}")
                print(f"总 Token 数: {session['total_tokens']}")
                print(f"{'='*60}\n")
                
                for msg in messages:
                    role_icon = "👤" if msg['role'] == 'user' else "🤖"
                    print(f"{role_icon} {msg['content']}\n")
                    
                    if msg.get('retrieved_chunks'):
                        print(f"   📚 检索了 {len(msg['retrieved_chunks'])} 个文档块")
                    if msg.get('processing_time'):
                        print(f"   ⏱️  耗时 {msg['processing_time']:.2f}秒")
                    print()
            else:
                print(f"❌ 获取历史失败: {response.text}")
        
        except Exception as e:
            print(f"❌ 获取历史失败: {e}")
    
    def interactive_chat(self):
        """交互式聊天"""
        print(f"\n💬 开始对话")
        print("输入消息发送，输入命令执行操作")
        print("命令列表:")
        print("  /history - 查看会话历史")
        print("  /clear   - 清屏")
        print("  /help    - 显示帮助")
        print("  /exit    - 退出")
        print()
        
        while True:
            try:
                user_input = input("👤 您: ").strip()
                
                if not user_input:
                    continue
                
                # 处理命令
                if user_input.startswith('/'):
                    command = user_input.lower()
                    
                    if command == '/exit' or command == '/quit':
                        print("再见！👋")
                        break
                    
                    elif command == '/history':
                        self.show_history()
                    
                    elif command == '/clear':
                        import os
                        os.system('cls' if os.name == 'nt' else 'clear')
                    
                    elif command == '/help':
                        print("\n命令列表:")
                        print("  /history - 查看会话历史")
                        print("  /clear   - 清屏")
                        print("  /help    - 显示帮助")
                        print("  /exit    - 退出")
                        print()
                    
                    else:
                        print(f"❌ 未知命令: {command}")
                    
                    continue
                
                # 发送消息
                self.send_message(user_input)
                print()
            
            except KeyboardInterrupt:
                print("\n\n再见！👋")
                break
            except EOFError:
                print("\n\n再见！👋")
                break


def main():
    """主函数"""
    print("=" * 60)
    print("🤖 RAG 智能对话系统")
    print("=" * 60)
    
    client = ChatClient()
    
    # 检查服务器
    print("\n🔍 检查服务器连接...")
    if not client.check_server():
        print("❌ 无法连接到服务器")
        print("请确保服务器正在运行: python main.py")
        sys.exit(1)
    
    print("✅ 服务器连接成功")
    
    # 选择知识库
    kbs = client.list_knowledge_bases()
    if not kbs:
        sys.exit(1)
    
    print("\n请选择知识库 ID: ", end='')
    try:
        kb_id = int(input().strip())
        
        # 验证知识库 ID
        if not any(kb['id'] == kb_id for kb in kbs):
            print(f"❌ 知识库 {kb_id} 不存在")
            sys.exit(1)
    except ValueError:
        print("❌ 无效的知识库 ID")
        sys.exit(1)
    
    # 选择搜索模式
    print("\n🔧 搜索配置:")
    print("  1. 仅向量搜索")
    print("  2. 仅图谱搜索")
    print("  3. 混合搜索（推荐）")
    print("选择模式 [1-3, 默认3]: ", end='')
    
    mode = input().strip() or "3"
    
    if mode == "1":
        use_vector, use_graph = True, False
    elif mode == "2":
        use_vector, use_graph = False, True
    else:
        use_vector, use_graph = True, True
    
    # 创建会话
    if not client.create_session(kb_id, use_vector, use_graph):
        sys.exit(1)
    
    # 开始聊天
    client.interactive_chat()


if __name__ == "__main__":
    main()

