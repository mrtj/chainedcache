import os.path

try:
    import boto3
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False

class BaseCache:
    
    def __init__(self, verbose=True):
        ''' Base class for cache instances. 
        
        Params:
            verbose (bool): Print cache related messages.
        '''
        self.verbose = verbose
        
    def message(self, msg):
        if self.verbose:
            print(msg)
    
    def put(self, key, data):
        ''' Puts an object in the cache. '''
        pass
    
    def get(self, key):
        ''' Gets an object from the cache. 
        
        If the object was not found, returns None.
        '''
        pass
    
    def remove(self, key):
        ''' Removes a data object key in the cache. '''
        pass
    
    def get_put(self, key, generator):
        ''' Gets an object from the cache or creates it.
        
        If the object was not found in the cache, calls generator() to create 
        it and puts the result in the cache.
        '''
        data = self.get(key)
        if not data:
            data = generator(key)
            self.put(key, data)
        return data



class DictCache(BaseCache):
    
    def __init__(self, **kwargs):
        ''' Simple dicitionary based in-memory cache. '''
        super().__init__(**kwargs)
        self.cache = {}
        
    def put(self, key, data):
        self.message(f"Putting '{key}' to {self}")
        self.cache[key] = data
    
    def get(self, key):
        data = self.cache.get(key)
        self.message(f"'{key}' was {'not ' if data is None else ''}found in {self}")
        return data
                     
    def remove(self, key):
        self.message(f"Removing '{key}' from {self}")
        self.cache.pop(key, None)
    
    def __repr__(self):
        return f'DictCache()'



class FileCache(BaseCache):
    
    def __init__(self, path, mode='text', put_transformer=None, get_transformer=None, **kwargs):
        '''
        Simple file based cache.
        
        Params:
            path (str): The cache folder path
            mode (str): The file write mode. 'text' and 'bytes' are supported.
            put_transformer (callable): Transform the data before being written to the file. Must return
                a bytes or text stream as specified by mode parameter.
            get_transformer (callable): Transform the data after being read from the file. Must accept
                a bytes or text stream as specified by mode parameter.
        '''
        super().__init__(**kwargs)
        self.path = path
        if not mode in ['text', 'bytes']:
            raise ValueError('Unsupported mode')
        self.mode = mode
        self.put_transformer = put_transformer
        self.get_transformer = get_transformer
        self.message(f'FileCache initialized at {self.path}')
        
    def filename(self, key):
        return os.path.join(self.path, key)
        
    def put(self, key, data):
        if callable(self.put_transformer):
            data = self.put_transformer(data)
        mode = 'w' if self.mode == 'text' else 'wb'
        self.message(f"Putting '{key}' to {self}")
        with open(self.filename(key), mode) as f:
            f.write(data)

    def get(self, key):
        filename = self.filename(key)
        if not os.path.isfile(filename):
            self.message(f"'{key}' was not found in {self}")
            return None
        self.message(f"'{key}' was found in {self}")
        mode = 'r' if self.mode == 'text' else 'rb'
        with open(filename, mode) as f:
            data = f.read()
        if callable(self.get_transformer):
            data = self.get_transformer(data)
        return data
    
    def remove(self, key):
        self.message(f"Removing '{key}' from {self}")
        filename = self.filename(key)
        if os.path.isfile(filename):
            os.remove(filename)
                     
    def __repr__(self):
        return f"FileCache(path='{self.path}', mode='{self.mode}')"



class S3Cache(BaseCache):
    
    def __init__(self, bucket, prefix, region='eu-west-1', 
                 put_transformer=None, get_transformer=None, **kwargs):
        '''
        A cache based on Amazon S3 service.
        
        You must install boto3 to be able to use this class.
        
        Params:
            bucket (str): The S3 bucket name
            prefix (str): The S3 key prefix
            put_transformer (callable): Transform the data before being written 
                to the file. Must return a bytes array or bytes output stream.
            get_transformer (callable): Transform the data after being read 
                from the file. Must accept a bytes input stream.
        '''
        if not HAS_BOTO3:
            raise ImportError('Please install boto3 in order to use S3Cache!')
        super().__init__(**kwargs)
        self.bucket = bucket
        self.prefix = prefix
        self.region = region
        self.put_transformer = put_transformer
        self.get_transformer = get_transformer
        self.session = boto3.session.Session(region_name=region)
        self.s3 = self.session.client('s3')
        self.message(f'S3Cache initialized at s3://{bucket}/{prefix}')
        
    def bucket_key(self, key):
        return os.path.join(self.prefix, key)

    def put(self, key, data):
        if callable(self.put_transformer):
            data = self.put_transformer(data)
        self.message(f"Putting '{key}' to {self}")
        self.s3.put_object(Body=data, Bucket=self.bucket, Key=self.bucket_key(key))
        
    def get(self, key):
        try:
            data = self.s3.get_object(Bucket=self.bucket, Key=self.bucket_key(key))['Body']
        except self.s3.exceptions.NoSuchKey as e:
            self.message(f"'{key}' was not found in {self}")
            return None
        self.message(f"'{key}' was found in {self}")
        if callable(self.get_transformer):
            data = self.get_transformer(data)
        return data
                     
    def remove(self, key):
        self.message(f"Removing '{key}' from {self}")
        self.s3.delete_object(Bucket=self.bucket, Key=self.bucket_key(key))
    
    def __repr__(self):
        return f"S3Cache(bucket='{self.bucket}', prefix='{self.prefix}', region='{self.region}')"

    
class ChainedCache(BaseCache):
    
    def __init__(self, caches):
        ''' A chained cache.
        
        You can initialize a ChainedCache with a list of other BaseCache 
        instances. When an object is requested, ChainedCache searches the 
        object in the cache instances one at a time and returns as soon as
        it is found. It also saves the object in the downstream cache instances.
        
        For example you can construct the following cache chain:

            dict_cache = DictCache()
            file_cache = FileCache(...)
            s3_cache = S3Cache(...)
            cache = ChainedCache([dict_cache, file_cache, s3_cache])

        This cache will first search the requested object in the in-memory
        dictionary, if it is not found than in the local file system, and
        if it is still not found, in the S3 bucket.
        '''
        self.caches = caches
        
    def get(self, key):
        data = None
        for idx, cache in enumerate(self.caches):
            data = cache.get(key)
            if data is not None:
                break
        if data is not None:
            for i in range(idx):
                self.caches[i].put(key, data)
        return data
    
    def put(self, key, data):
        for cache in reversed(self.caches):
            cache.put(key, data)

    def remove(self, key):
        for cache in reversed(self.caches):
            cache.remove(key)

    def __repr__(self):
        return f"CascadedCache(caches={self.caches})"
