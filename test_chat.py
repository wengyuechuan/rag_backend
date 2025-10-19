"""
对话接口测试脚本
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000/api/v1"


def test_create_session():
    """测试创建会话"""
    print("\n" + "="*60)
    print("测试 1: 创建会话")
    print("="*60)
    
    response = requests.post(
        f"{BASE_URL}/chat/sessions",
        json={
            "knowledge_base_id": 1,
            "title": "测试对话",
            "use_vector_search": True,
            "use_graph_search": True,
            "search_top_k": 5
        }
    )
    
    if response.status_code == 201:
        session = response.json()
        print(f"✅ 会话创建成功")
        print(f"   会话 ID: {session['id']}")
        print(f"   标题: {session['title']}")
        print(f"   知识库 ID: {session['knowledge_base_id']}")
        print(f"   向量搜索: {session['use_vector_search']}")
        print(f"   图谱搜索: {session['use_graph_search']}")
        return session['id']
    else:
        print(f"❌ 创建失败: {response.text}")
        return None


def test_list_sessions():
    """测试获取会话列表"""
    print("\n" + "="*60)
    print("测试 2: 获取会话列表")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/chat/sessions?limit=10")
    
    if response.status_code == 200:
        sessions = response.json()
        print(f"✅ 获取成功，共 {len(sessions)} 个会话")
        for session in sessions[:3]:
            print(f"   - ID: {session['id']}, 标题: {session['title']}, 消息数: {session['message_count']}")
    else:
        print(f"❌ 获取失败: {response.text}")


def test_chat_stream(session_id, message):
    """测试流式对话"""
    print("\n" + "="*60)
    print(f"测试 3: 流式对话")
    print("="*60)
    print(f"👤 用户: {message}")
    
    response = requests.post(
        f"{BASE_URL}/chat/completions",
        json={
            "session_id": session_id,
            "message": message,
            "stream": True,
            "temperature": 0.7
        },
        stream=True
    )
    
    if response.status_code == 200:
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
                        
                        elif data['type'] == 'chunk':
                            print(data['data'], end='', flush=True)
                        
                        elif data['type'] == 'done':
                            print(f"\n\n✅ 完成")
                            print(f"   消息 ID: {data['data']['message_id']}")
                            print(f"   处理时间: {data['data']['processing_time']:.2f}秒")
                            print(f"   检索文档块: {chunks_count}")
                            print(f"   检索实体: {entities_count}")
                        
                        elif data['type'] == 'error':
                            print(f"\n❌ 错误: {data['data']}")
                    
                    except json.JSONDecodeError as e:
                        print(f"\n⚠️  JSON 解析错误: {e}")
    else:
        print(f"❌ 对话失败: {response.text}")


def test_chat_non_stream(session_id, message):
    """测试非流式对话"""
    print("\n" + "="*60)
    print(f"测试 4: 非流式对话")
    print("="*60)
    print(f"👤 用户: {message}")
    
    response = requests.post(
        f"{BASE_URL}/chat/completions",
        json={
            "session_id": session_id,
            "message": message,
            "stream": False,
            "temperature": 0.7
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"🤖 AI: {result['content'][:200]}...")
        print(f"\n✅ 完成")
        print(f"   消息 ID: {result['message_id']}")
        print(f"   处理时间: {result['processing_time']:.2f}秒")
        print(f"   检索文档块: {len(result.get('retrieved_chunks', []))}")
        print(f"   检索实体: {len(result.get('retrieved_entities', []))}")
    else:
        print(f"❌ 对话失败: {response.text}")


def test_get_history(session_id):
    """测试获取会话历史"""
    print("\n" + "="*60)
    print("测试 5: 获取会话历史")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/chat/sessions/{session_id}/history")
    
    if response.status_code == 200:
        history = response.json()
        print(f"✅ 获取成功")
        print(f"   会话 ID: {history['session']['id']}")
        print(f"   标题: {history['session']['title']}")
        print(f"   总消息数: {history['total']}")
        print(f"   总 Token 数: {history['session']['total_tokens']}")
        
        print(f"\n对话历史:")
        for msg in history['messages']:
            role_icon = "👤" if msg['role'] == 'user' else "🤖"
            print(f"\n{role_icon} [{msg['created_at']}]")
            print(f"   {msg['content'][:100]}...")
            if msg.get('retrieved_chunks'):
                print(f"   📚 使用了 {len(msg['retrieved_chunks'])} 个文档块")
    else:
        print(f"❌ 获取失败: {response.text}")


def test_update_session(session_id):
    """测试更新会话"""
    print("\n" + "="*60)
    print("测试 6: 更新会话")
    print("="*60)
    
    response = requests.patch(
        f"{BASE_URL}/chat/sessions/{session_id}",
        json={
            "title": "更新后的标题",
            "search_top_k": 10
        }
    )
    
    if response.status_code == 200:
        session = response.json()
        print(f"✅ 更新成功")
        print(f"   新标题: {session['title']}")
        print(f"   新 Top-K: {session['search_top_k']}")
    else:
        print(f"❌ 更新失败: {response.text}")


def main():
    print("\n" + "🚀"*30)
    print("对话接口测试")
    print("🚀"*30)
    
    # 检查服务是否可用
    try:
        response = requests.get(f"{BASE_URL.replace('/api/v1', '')}/health")
        if response.status_code != 200:
            print("❌ 服务不可用，请先启动服务器")
            return
    except Exception as e:
        print(f"❌ 无法连接到服务器: {e}")
        print("请确保服务器正在运行: python main.py")
        return
    
    # 测试流程
    session_id = None
    
    try:
        # 1. 创建会话
        session_id = test_create_session()
        if not session_id:
            print("❌ 无法创建会话，测试终止")
            return
        
        time.sleep(1)
        
        # 2. 获取会话列表
        test_list_sessions()
        time.sleep(1)
        
        # 3. 流式对话
        test_chat_stream(session_id, "小明的父亲是谁？")
        time.sleep(2)
        
        # 4. 继续对话（测试滑动窗口）
        test_chat_stream(session_id, "他的母亲呢？")
        time.sleep(2)
        
        # 5. 非流式对话
        test_chat_non_stream(session_id, "他们住在哪里？")
        time.sleep(1)
        
        # 6. 获取会话历史
        test_get_history(session_id)
        time.sleep(1)
        
        # 7. 更新会话
        test_update_session(session_id)
        
        print("\n" + "✅"*30)
        print("所有测试完成！")
        print("✅"*30 + "\n")
        
    except KeyboardInterrupt:
        print("\n\n测试被中断")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

