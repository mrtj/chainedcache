# chainedcache

Simple python cache system.

## Installation

```bash
$ python -m pip install git+https://github.com/mrtj/chainedcache
```

## Usage

```python
json2bytes = lambda d: json.dumps(d).encode('UTF-8')
bytes2json = lambda d: json.loads(d.decode('UTF-8'))
stream2json = lambda d: json.load(d)

dict_cache = DictCache()

file_cache = FileCache('./cache', mode='bytes', 
                       put_transformer=json2bytes, get_transformer=bytes2json)

s3_cache = S3Cache('my_s3_bucket', 'cache', region='us-east-1', 
                   put_transformer=json2bytes, get_transformer=stream2json)

cache = ChainedCache([dict_cache, file_cache, s3_cache])

def data_generator(key):
    return { "the_key_is": key }

json_data = cache.get_put("hello", data_generator)
```
