"""
MongoDB Client for Gather Items
Handles reading and writing gather items to MongoDB
"""
import os
import structlog
from typing import List, Dict, Any, Optional
from datetime import datetime

try:
    from pymongo import MongoClient
    from bson import ObjectId
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False
    MongoClient = None
    ObjectId = None

logger = structlog.get_logger(__name__)

# MongoDB connection
_mongo_client: Optional[Any] = None


def get_mongo_client():
    """
    Get or create MongoDB client
    """
    global _mongo_client

    if not PYMONGO_AVAILABLE:
        logger.warning("pymongo not available, MongoDB operations will fail")
        return None

    if _mongo_client is None:
        mongo_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
        _mongo_client = MongoClient(mongo_uri)
        logger.info("MongoDB client initialized", uri=mongo_uri.split('@')[-1])  # Hide credentials

    return _mongo_client


def get_gather_collection(project_id: str):
    """
    Get gather collection for a project
    Collection name: aladdin-gather-{projectId}
    """
    client = get_mongo_client()
    db_name = os.getenv('MONGODB_DATABASE', 'aladdin')
    db = client[db_name]
    
    collection_name = f"aladdin-gather-{project_id}"
    return db[collection_name]


def read_gather_items(project_id: str) -> List[Dict[str, Any]]:
    """
    Read all gather items for a project
    
    Args:
        project_id: Project identifier
    
    Returns:
        List of gather items
    """
    try:
        collection = get_gather_collection(project_id)
        
        # Query all items, sorted by creation date
        items = list(collection.find({}).sort('createdAt', -1))
        
        # Convert ObjectId to string
        for item in items:
            if '_id' in item:
                item['_id'] = str(item['_id'])
        
        logger.info(
            "Read gather items from MongoDB",
            project_id=project_id,
            count=len(items)
        )
        
        return items
        
    except Exception as e:
        logger.error(
            "Error reading gather items",
            project_id=project_id,
            error=str(e),
            exc_info=True
        )
        return []


def save_to_gather_db(
    project_id: str,
    items: List[Dict[str, Any]],
    user_id: str,
    automation_metadata: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Save gather items to MongoDB
    
    Args:
        project_id: Project identifier
        items: List of items to save
        user_id: User who triggered automation
        automation_metadata: Metadata about automation task
    
    Returns:
        List of saved items with IDs
    """
    if not items:
        return []
    
    try:
        collection = get_gather_collection(project_id)
        
        # Prepare items for insertion
        now = datetime.utcnow()
        docs = []
        
        for item in items:
            doc = {
                'projectId': project_id,
                'content': item.get('content', ''),
                'summary': item.get('summary', ''),
                'context': item.get('context', ''),
                'imageUrl': item.get('imageUrl'),
                'documentUrl': item.get('documentUrl'),
                'extractedText': item.get('extractedText'),
                'duplicateCheckScore': item.get('duplicateCheckScore'),
                
                # Automation fields
                'isAutomated': True,
                'automationMetadata': {
                    'taskId': automation_metadata.get('taskId'),
                    'department': automation_metadata.get('department'),
                    'departmentName': automation_metadata.get('departmentName'),
                    'departmentNumber': automation_metadata.get('departmentNumber'),
                    'iteration': automation_metadata.get('iteration'),
                    'qualityScore': automation_metadata.get('qualityScore'),
                    'model': automation_metadata.get('model'),
                    'basedOnNodes': item.get('basedOnNodes', [])
                },
                
                'createdAt': now,
                'createdBy': user_id,
                'lastUpdated': now
            }
            docs.append(doc)
        
        # Insert documents
        result = collection.insert_many(docs)
        
        # Add IDs to items
        for i, item_id in enumerate(result.inserted_ids):
            docs[i]['_id'] = str(item_id)
        
        logger.info(
            "Saved gather items to MongoDB",
            project_id=project_id,
            count=len(docs),
            department=automation_metadata.get('department')
        )
        
        return docs
        
    except Exception as e:
        logger.error(
            "Error saving gather items",
            project_id=project_id,
            error=str(e),
            exc_info=True
        )
        raise


def get_items_by_department(
    project_id: str,
    department: str
) -> List[Dict[str, Any]]:
    """
    Get gather items for a specific department
    
    Args:
        project_id: Project identifier
        department: Department slug
    
    Returns:
        List of gather items for the department
    """
    try:
        collection = get_gather_collection(project_id)
        
        items = list(collection.find({
            'automationMetadata.department': department
        }).sort('createdAt', -1))
        
        # Convert ObjectId to string
        for item in items:
            if '_id' in item:
                item['_id'] = str(item['_id'])
        
        logger.info(
            "Read department gather items",
            project_id=project_id,
            department=department,
            count=len(items)
        )
        
        return items
        
    except Exception as e:
        logger.error(
            "Error reading department items",
            project_id=project_id,
            department=department,
            error=str(e),
            exc_info=True
        )
        return []


def get_automated_items(project_id: str) -> List[Dict[str, Any]]:
    """
    Get only automated gather items
    
    Args:
        project_id: Project identifier
    
    Returns:
        List of automated gather items
    """
    try:
        collection = get_gather_collection(project_id)
        
        items = list(collection.find({
            'isAutomated': True
        }).sort('createdAt', -1))
        
        # Convert ObjectId to string
        for item in items:
            if '_id' in item:
                item['_id'] = str(item['_id'])
        
        logger.info(
            "Read automated gather items",
            project_id=project_id,
            count=len(items)
        )
        
        return items
        
    except Exception as e:
        logger.error(
            "Error reading automated items",
            project_id=project_id,
            error=str(e),
            exc_info=True
        )
        return []

