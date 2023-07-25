from copy import deepcopy
from .contants import EMPTY_FIELD

# ckanField.title -> dataDict.name (internal naming)
ckanFieldMapping = {
    "title": "title",
    "description": "notes",

    # Comma seperated tags, e.g. "Housing,Transportation"
    "tags": "tags",

    # e.g. '7e16bc89-a6d1-44b4-85e4-692311d28e73'
    "id": "id",

    
    "author": "author",
    "author_email": "author_email",
    "name": "name",
    "version": "version",
    "format": "file_format",
    "source": "url"
}
ckanFieldKeys = [
    "name", "title", "notes", "tags", "id", "pkg_name", "author", "author_email",
    "file_format", "url", "version"
]

class CKANField(dict):
    """dot.notation access to dictionary attributes"""
    # __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

    def __init__(self, data: dict):
        ckanFields = {}
        for key in ckanFieldKeys:
            ckanFields[key] = data.get(key)
        super().__init__(ckanFields)
    
    def __getattr__(self, key):
        if key == 'id':
            # 'pkg_name' should be used on update, 'id' is used on create
            return self.get('pkg_name') or self.get('id')
        elif key == 'tags':
            # Return comma separated tags
            return ', '.join([tag["name"] for tag in self.get('tags')])
        elif self.get(ckanFieldMapping.get(key)) is not None:
            return self.get(ckanFieldMapping.get(key))
        else:
            return EMPTY_FIELD
