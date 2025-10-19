"""
文档分块工具类
支持多种分块策略：固定大小分块、递归分块、语义分块等
"""

import re
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass


@dataclass
class ChunkMetadata:
    """块的元数据"""
    chunk_id: int
    start_pos: int
    end_pos: int
    chunk_size: int
    strategy: str


class TextChunker:
    """
    文档分块工具类
    
    支持的分块策略：
    1. 固定大小分块 (fixed_size_chunking)
    2. 递归分块 (recursive_chunking)
    3. 语义分块 (semantic_chunking)
    4. 按分隔符分块 (split_by_separator)
    5. 按段落分块 (paragraph_chunking)
    """
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        length_function: Optional[Callable[[str], int]] = None,
        keep_separator: bool = True
    ):
        """
        初始化分块器
        
        Args:
            chunk_size: 块的最大大小（字符数或tokens数）
            chunk_overlap: 相邻块之间的重叠大小
            length_function: 自定义长度计算函数（默认使用len）
            keep_separator: 是否保留分隔符
        """
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap 必须小于 chunk_size")
        
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.length_function = length_function or len
        self.keep_separator = keep_separator
    
    def fixed_size_chunking(
        self, 
        text: str, 
        with_metadata: bool = False
    ) -> List[str] | List[Dict]:
        """
        固定大小分块：按固定大小切分文本，支持重叠
        
        Args:
            text: 输入文本
            with_metadata: 是否返回元数据
            
        Returns:
            分块后的文本列表或包含元数据的字典列表
        """
        chunks = []
        start = 0
        chunk_id = 0
        
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunk_text = text[start:end]
            
            if with_metadata:
                chunks.append({
                    'text': chunk_text,
                    'metadata': ChunkMetadata(
                        chunk_id=chunk_id,
                        start_pos=start,
                        end_pos=end,
                        chunk_size=len(chunk_text),
                        strategy='fixed_size'
                    )
                })
            else:
                chunks.append(chunk_text)
            
            chunk_id += 1
            start = end - self.chunk_overlap
            
            # 防止无限循环
            if start >= len(text) - self.chunk_overlap:
                break
        
        return chunks
    
    def recursive_chunking(
        self,
        text: str,
        separators: Optional[List[str]] = None,
        with_metadata: bool = False
    ) -> List[str] | List[Dict]:
        """
        递归分块：使用层级分隔符递归地分割文本
        
        Args:
            text: 输入文本
            separators: 分隔符列表，按优先级从高到低排序
            with_metadata: 是否返回元数据
            
        Returns:
            分块后的文本列表或包含元数据的字典列表
        """
        if separators is None:
            # 默认分隔符：段落 -> 句子 -> 单词
            separators = ["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]
        
        chunks = self._recursive_split(text, separators)
        
        if with_metadata:
            result = []
            pos = 0
            for i, chunk in enumerate(chunks):
                start = text.find(chunk, pos)
                end = start + len(chunk)
                result.append({
                    'text': chunk,
                    'metadata': ChunkMetadata(
                        chunk_id=i,
                        start_pos=start,
                        end_pos=end,
                        chunk_size=len(chunk),
                        strategy='recursive'
                    )
                })
                pos = end
            return result
        
        return chunks
    
    def _recursive_split(self, text: str, separators: List[str]) -> List[str]:
        """递归分割的内部实现"""
        if not separators:
            # 如果没有更多分隔符，强制按大小切分
            return self._force_split(text)
        
        separator = separators[0]
        remaining_separators = separators[1:]
        
        # 如果文本已经足够小，直接返回
        if self.length_function(text) <= self.chunk_size:
            return [text] if text else []
        
        # 使用当前分隔符分割
        if separator:
            splits = text.split(separator)
            if self.keep_separator and separator:
                # 保留分隔符
                splits = [s + separator if i < len(splits) - 1 else s 
                         for i, s in enumerate(splits)]
        else:
            # 空分隔符，按字符分割
            return self._force_split(text)
        
        # 合并小块并递归处理大块
        chunks = []
        current_chunk = []
        current_size = 0
        
        for split in splits:
            split_size = self.length_function(split)
            
            # 如果单个split就超过大小限制，需要递归分割
            if split_size > self.chunk_size:
                # 先保存当前积累的块
                if current_chunk:
                    chunks.append(separator.join(current_chunk) if separator else "".join(current_chunk))
                    current_chunk = []
                    current_size = 0
                
                # 递归处理大块
                sub_chunks = self._recursive_split(split, remaining_separators)
                chunks.extend(sub_chunks)
            
            # 如果加入这个split会超过大小限制
            elif current_size + split_size > self.chunk_size and current_chunk:
                # 保存当前块
                chunks.append(separator.join(current_chunk) if separator else "".join(current_chunk))
                current_chunk = [split]
                current_size = split_size
            
            # 可以加入当前块
            else:
                current_chunk.append(split)
                current_size += split_size
        
        # 保存最后的块
        if current_chunk:
            chunks.append(separator.join(current_chunk) if separator else "".join(current_chunk))
        
        # 添加重叠
        if self.chunk_overlap > 0:
            chunks = self._add_overlap(chunks)
        
        return chunks
    
    def _force_split(self, text: str) -> List[str]:
        """强制按大小分割文本"""
        chunks = []
        for i in range(0, len(text), self.chunk_size - self.chunk_overlap):
            chunks.append(text[i:i + self.chunk_size])
        return chunks
    
    def _add_overlap(self, chunks: List[str]) -> List[str]:
        """为块添加重叠"""
        if len(chunks) <= 1 or self.chunk_overlap == 0:
            return chunks
        
        overlapped_chunks = []
        for i, chunk in enumerate(chunks):
            if i == 0:
                overlapped_chunks.append(chunk)
            else:
                # 从前一个块的末尾取重叠部分
                prev_chunk = chunks[i - 1]
                overlap_text = prev_chunk[-self.chunk_overlap:] if len(prev_chunk) > self.chunk_overlap else prev_chunk
                overlapped_chunks.append(overlap_text + chunk)
        
        return overlapped_chunks
    
    def semantic_chunking(
        self,
        text: str,
        language: str = 'zh',
        with_metadata: bool = False
    ) -> List[str] | List[Dict]:
        """
        语义分块：基于句子边界进行智能分块
        
        Args:
            text: 输入文本
            language: 语言类型 ('zh' 中文, 'en' 英文)
            with_metadata: 是否返回元数据
            
        Returns:
            分块后的文本列表或包含元数据的字典列表
        """
        # 根据语言选择句子分割模式
        if language == 'zh':
            # 中文句子分割
            sentence_pattern = r'[^。！？；…]+[。！？；…]?'
        else:
            # 英文句子分割
            sentence_pattern = r'[^.!?]+[.!?]?'
        
        sentences = re.findall(sentence_pattern, text)
        
        chunks = []
        current_chunk = ""
        current_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # 计算加入新句子后的大小
            test_chunk = current_chunk + sentence
            
            if self.length_function(test_chunk) > self.chunk_size and current_chunk:
                # 当前块已满，保存并开始新块
                chunks.append(current_chunk.strip())
                
                # 使用重叠策略：保留最后几个句子
                if self.chunk_overlap > 0 and current_sentences:
                    overlap_text = ""
                    for prev_sent in reversed(current_sentences):
                        if len(overlap_text) + len(prev_sent) <= self.chunk_overlap:
                            overlap_text = prev_sent + overlap_text
                        else:
                            break
                    current_chunk = overlap_text + sentence
                    current_sentences = [overlap_text, sentence] if overlap_text else [sentence]
                else:
                    current_chunk = sentence
                    current_sentences = [sentence]
            else:
                # 继续累积到当前块
                current_chunk = test_chunk
                current_sentences.append(sentence)
        
        # 添加最后一个块
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        if with_metadata:
            result = []
            pos = 0
            for i, chunk in enumerate(chunks):
                start = text.find(chunk[:50], pos)  # 使用前50个字符定位
                end = start + len(chunk)
                result.append({
                    'text': chunk,
                    'metadata': ChunkMetadata(
                        chunk_id=i,
                        start_pos=start,
                        end_pos=end,
                        chunk_size=len(chunk),
                        strategy='semantic'
                    )
                })
                pos = end
            return result
        
        return chunks
    
    def split_by_separator(
        self,
        text: str,
        separator: str = "\n",
        with_metadata: bool = False
    ) -> List[str] | List[Dict]:
        """
        按指定分隔符分块
        
        Args:
            text: 输入文本
            separator: 分隔符
            with_metadata: 是否返回元数据
            
        Returns:
            分块后的文本列表或包含元数据的字典列表
        """
        parts = text.split(separator)
        chunks = []
        
        for i, part in enumerate(parts):
            if not part.strip():
                continue
            
            chunk_text = part if not self.keep_separator else part + separator
            
            if with_metadata:
                chunks.append({
                    'text': chunk_text,
                    'metadata': ChunkMetadata(
                        chunk_id=i,
                        start_pos=-1,  # 简化处理
                        end_pos=-1,
                        chunk_size=len(chunk_text),
                        strategy='separator'
                    )
                })
            else:
                chunks.append(chunk_text)
        
        return chunks
    
    def paragraph_chunking(
        self,
        text: str,
        with_metadata: bool = False
    ) -> List[str] | List[Dict]:
        """
        按段落分块（段落之间由空行分隔）
        
        Args:
            text: 输入文本
            with_metadata: 是否返回元数据
            
        Returns:
            分块后的文本列表或包含元数据的字典列表
        """
        # 按空行分割段落
        paragraphs = re.split(r'\n\s*\n', text)
        chunks = []
        current_chunk = ""
        chunk_id = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # 如果单个段落就超过大小限制
            if self.length_function(para) > self.chunk_size:
                # 先保存当前块
                if current_chunk:
                    if with_metadata:
                        chunks.append({
                            'text': current_chunk,
                            'metadata': ChunkMetadata(
                                chunk_id=chunk_id,
                                start_pos=-1,
                                end_pos=-1,
                                chunk_size=len(current_chunk),
                                strategy='paragraph'
                            )
                        })
                    else:
                        chunks.append(current_chunk)
                    chunk_id += 1
                    current_chunk = ""
                
                # 对大段落进行递归分块
                sub_chunks = self.recursive_chunking(para)
                for sub_chunk in sub_chunks:
                    if with_metadata:
                        chunks.append({
                            'text': sub_chunk,
                            'metadata': ChunkMetadata(
                                chunk_id=chunk_id,
                                start_pos=-1,
                                end_pos=-1,
                                chunk_size=len(sub_chunk),
                                strategy='paragraph'
                            )
                        })
                    else:
                        chunks.append(sub_chunk)
                    chunk_id += 1
            
            # 如果加入段落后超过大小限制
            elif self.length_function(current_chunk + "\n\n" + para) > self.chunk_size and current_chunk:
                if with_metadata:
                    chunks.append({
                        'text': current_chunk,
                        'metadata': ChunkMetadata(
                            chunk_id=chunk_id,
                            start_pos=-1,
                            end_pos=-1,
                            chunk_size=len(current_chunk),
                            strategy='paragraph'
                        )
                    })
                else:
                    chunks.append(current_chunk)
                chunk_id += 1
                current_chunk = para
            
            # 可以加入当前块
            else:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
        
        # 添加最后一个块
        if current_chunk:
            if with_metadata:
                chunks.append({
                    'text': current_chunk,
                    'metadata': ChunkMetadata(
                        chunk_id=chunk_id,
                        start_pos=-1,
                        end_pos=-1,
                        chunk_size=len(current_chunk),
                        strategy='paragraph'
                    )
                })
            else:
                chunks.append(current_chunk)
        
        return chunks


def test_chunker():
    """测试函数"""
    print("=" * 80)
    print("文档分块工具测试")
    print("=" * 80)
    
    # 测试文本
    chinese_text = """
人工智能（Artificial Intelligence，AI）是计算机科学的一个分支。它企图了解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。

该领域的研究包括机器人、语言识别、图像识别、自然语言处理和专家系统等。人工智能从诞生以来，理论和技术日益成熟，应用领域也不断扩大。

可以设想，未来人工智能带来的科技产品，将会是人类智慧的"容器"。人工智能可以对人的意识、思维的信息过程进行模拟。

人工智能不是人的智能，但能像人那样思考、也可能超过人的智能。人工智能是一门极富挑战性的科学，从事这项工作的人必须懂得计算机知识，心理学和哲学。

人工智能是包括十分广泛的科学，它由不同的领域组成，如机器学习、计算机视觉等等。总的说来，人工智能研究的一个主要目标是使机器能够胜任一些通常需要人类智能才能完成的复杂工作。
    """.strip()
    
    english_text = """
Machine learning is a subset of artificial intelligence. It focuses on the development of algorithms and statistical models. These enable computers to improve their performance on tasks through experience.

Deep learning is a type of machine learning. It uses neural networks with multiple layers. This approach has led to breakthroughs in image recognition, natural language processing, and many other fields.

The future of AI looks promising. Researchers continue to push the boundaries of what's possible. New applications emerge regularly across various industries.
    """.strip()
    
    # 测试1: 固定大小分块
    print("\n【测试1: 固定大小分块】")
    print("-" * 80)
    chunker = TextChunker(chunk_size=100, chunk_overlap=20)
    chunks = chunker.fixed_size_chunking(chinese_text)
    for i, chunk in enumerate(chunks, 1):
        print(f"块 {i} (长度: {len(chunk)}): {chunk[:50]}...")
    
    # 测试2: 递归分块
    print("\n【测试2: 递归分块】")
    print("-" * 80)
    chunker = TextChunker(chunk_size=150, chunk_overlap=30)
    chunks = chunker.recursive_chunking(chinese_text)
    for i, chunk in enumerate(chunks, 1):
        print(f"块 {i} (长度: {len(chunk)}): {chunk[:50]}...")
    
    # 测试3: 语义分块（中文）
    print("\n【测试3: 语义分块（中文）】")
    print("-" * 80)
    chunker = TextChunker(chunk_size=150, chunk_overlap=30)
    chunks = chunker.semantic_chunking(chinese_text, language='zh')
    for i, chunk in enumerate(chunks, 1):
        print(f"块 {i} (长度: {len(chunk)}): {chunk[:50]}...")
    
    # 测试4: 语义分块（英文）
    print("\n【测试4: 语义分块（英文）】")
    print("-" * 80)
    chunker = TextChunker(chunk_size=100, chunk_overlap=20)
    chunks = chunker.semantic_chunking(english_text, language='en')
    for i, chunk in enumerate(chunks, 1):
        print(f"块 {i} (长度: {len(chunk)}): {chunk}")
    
    # 测试5: 段落分块
    print("\n【测试5: 段落分块】")
    print("-" * 80)
    chunker = TextChunker(chunk_size=200, chunk_overlap=0)
    chunks = chunker.paragraph_chunking(chinese_text)
    for i, chunk in enumerate(chunks, 1):
        print(f"块 {i} (长度: {len(chunk)}): {chunk[:50]}...")
    
    # 测试6: 带元数据的分块
    print("\n【测试6: 带元数据的分块】")
    print("-" * 80)
    chunker = TextChunker(chunk_size=100, chunk_overlap=20)
    chunks_with_meta = chunker.fixed_size_chunking(chinese_text[:200], with_metadata=True)
    for item in chunks_with_meta:
        print(f"块ID: {item['metadata'].chunk_id}, "
              f"位置: {item['metadata'].start_pos}-{item['metadata'].end_pos}, "
              f"大小: {item['metadata'].chunk_size}, "
              f"策略: {item['metadata'].strategy}")
        print(f"内容: {item['text'][:50]}...")
        print()
    
    # 测试7: 自定义分隔符分块
    print("\n【测试7: 自定义分隔符分块】")
    print("-" * 80)
    custom_text = "第一部分内容|第二部分内容|第三部分内容|第四部分内容"
    chunker = TextChunker(chunk_size=1000, chunk_overlap=0, keep_separator=False)
    chunks = chunker.split_by_separator(custom_text, separator="|")
    for i, chunk in enumerate(chunks, 1):
        print(f"块 {i}: {chunk}")
    
    print("\n" + "=" * 80)
    print("测试完成！")
    print("=" * 80)


if __name__ == "__main__":
    test_chunker()

