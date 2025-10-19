"""
基础模型类
提供通用的数据模型功能
"""

from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, field, asdict
import json
import uuid


@dataclass
class BaseModel:
    """
    基础模型类
    所有数据模型的基类
    """
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        
        Returns:
            字典表示
        """
        data = asdict(self)
        # 转换 datetime 为 ISO 格式字符串
        if isinstance(data.get('created_at'), datetime):
            data['created_at'] = data['created_at'].isoformat()
        if isinstance(data.get('updated_at'), datetime):
            data['updated_at'] = data['updated_at'].isoformat()
        return data
    
    def to_json(self, indent: Optional[int] = None) -> str:
        """
        转换为 JSON 字符串
        
        Args:
            indent: JSON 缩进
            
        Returns:
            JSON 字符串
        """
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseModel':
        """
        从字典创建实例
        
        Args:
            data: 字典数据
            
        Returns:
            模型实例
        """
        # 转换 ISO 格式字符串为 datetime
        if isinstance(data.get('created_at'), str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if isinstance(data.get('updated_at'), str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'BaseModel':
        """
        从 JSON 字符串创建实例
        
        Args:
            json_str: JSON 字符串
            
        Returns:
            模型实例
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def update_metadata(self, key: str, value: Any):
        """
        更新元数据
        
        Args:
            key: 键
            value: 值
        """
        self.metadata[key] = value
        self.updated_at = datetime.now()
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """
        获取元数据
        
        Args:
            key: 键
            default: 默认值
            
        Returns:
            元数据值
        """
        return self.metadata.get(key, default)
    
    def __repr__(self) -> str:
        """字符串表示"""
        return f"{self.__class__.__name__}(id={self.id[:8]}...)"

