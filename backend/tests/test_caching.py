from app.worker.cache import InferenceCache


def test_inference_cache(tmp_path):
    cache = InferenceCache(cache_dir=str(tmp_path))
    
    # Cache miss
    assert cache.get("modelA", "promptA", {"temp": 0}) is None
    
    # Cache hit
    cache.set("modelA", "promptA", {"temp": 0}, {"result": "success"})
    hit = cache.get("modelA", "promptA", {"temp": 0})
    assert hit == {"result": "success"}
    
    # Different setting misses
    assert cache.get("modelA", "promptA", {"temp": 1}) is None
