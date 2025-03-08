using System;
using System.Collections.Generic;
using System.Threading;

namespace EnhanceExcel2Anything
{
    public class AutoLru<TKey, TValue> where TValue : class
    {
        private class CacheItem
        {
            public TValue Value;
            public LinkedListNode<TKey> Node;
            public int ActiveUsageCount;
            public DateTime LastAccessTime;
        }

        private readonly Dictionary<TKey, CacheItem> _items = new();
        private readonly LinkedList<TKey> _accessOrder = new();
        private readonly ReaderWriterLockSlim _lock = new();

        private int _currentCount;
        private readonly int _maxCount;
        private Timer _cleanupTimer;

        /// <summary>
        /// 全自动LRU管理，根据限定最高个数，自动清理最不活跃的
        /// </summary>
        /// <param name="maxCount">容器个数</param>
        /// <param name="cleanupInterval">定时清理时间</param>
        public AutoLru(int maxCount, TimeSpan cleanupInterval)
        {
            _maxCount = maxCount;
            _cleanupTimer = new Timer(_ => Cleanup(), null, cleanupInterval, cleanupInterval);
        }

        /// <summary>
        /// 获取或添加一个值，如果已存在，则更新访问时间，否则创建一个新值并添加到容器中。
        /// </summary>
        /// <param name="key"></param>
        /// <param name="valueFactory"></param>
        /// <returns></returns>
        public TValue GetOrAdd(TKey key, Func<TValue> valueFactory)
        {
            _lock.EnterUpgradeableReadLock();
            try
            {
                if (_items.TryGetValue(key, out var item))
                {
                    UpdateAccess(item);
                    return item.Value;
                }

                _lock.EnterWriteLock();
                try
                {
                    while (_currentCount >= _maxCount)
                    {
                        EvictOne();
                    }

                    var value = valueFactory();
                    var node = new LinkedListNode<TKey>(key);

                    _accessOrder.AddFirst(node);
                    _items.Add(key, new CacheItem
                    {
                        Value = value,
                        Node = node,
                        LastAccessTime = DateTime.UtcNow
                    });
                    Interlocked.Increment(ref _currentCount);
                    return value;
                }
                finally
                {
                    _lock.ExitWriteLock();
                }
            }
            finally
            {
                _lock.ExitUpgradeableReadLock();
            }
        }

        /// <summary>
        /// 标记一个值被使用,增加内部引用计数
        /// </summary>
        /// <param name="value"></param>
        public void MarkUsage(TValue value)
        {
            _lock.EnterReadLock();
            try
            {
                foreach (var item in _items)
                {
                    if (ReferenceEquals(item.Value.Value, value))
                    {
                        Interlocked.Increment(ref item.Value.ActiveUsageCount);
                        break;
                    }
                }
            }
            finally
            {
                _lock.ExitReadLock();
            }
        }

        /// <summary>
        /// 强制清空所有缓存
        /// </summary>
        public void Clear()
        {
            _lock.EnterWriteLock();
            try
            {
                _accessOrder.Clear();
                _items.Clear();
                _currentCount = 0;
            }
            finally
            {
                _lock.ExitWriteLock();
            }
        }

        private void UpdateAccess(CacheItem item)
        {
            _lock.EnterWriteLock();
            try
            {
                _accessOrder.Remove(item.Node);
                _accessOrder.AddFirst(item.Node);
                item.LastAccessTime = DateTime.UtcNow;
                item.ActiveUsageCount = Math.Max(0, item.ActiveUsageCount - 1);
            }
            finally
            {
                _lock.ExitWriteLock();
            }
        }

        private void EvictOne()
        {
            var node = _accessOrder.Last;
            while (node != null)
            {
                if (_items.TryGetValue(node.Value, out var item))
                {
                    // 引用次数小于等于0，则移除该节点
                    if (item.ActiveUsageCount <= 0)
                    {
                        _accessOrder.Remove(node);
                        _items.Remove(node.Value);
                        Interlocked.Decrement(ref _currentCount);
                        (item.Value as IDisposable)?.Dispose();
                        return;
                    }
                }

                node = node.Previous;
            }
        }

        private void Cleanup()
        {
            _lock.EnterWriteLock();
            try
            {
                var threshold = DateTime.UtcNow.AddMilliseconds(-5);
                var nodesToRemove = new List<LinkedListNode<TKey>>();

                var node = _accessOrder.Last;
                while (node != null)
                {
                    if (_items.TryGetValue(node.Value, out var item))
                    {
                        if (item.LastAccessTime < threshold && item.ActiveUsageCount <= 0)
                        {
                            nodesToRemove.Add(node);
                        }
                    }

                    node = node.Previous;
                }

                foreach (var listNode in nodesToRemove)
                {
                    _accessOrder.Remove(listNode);
                    _items.Remove(listNode.Value);
                    Interlocked.Decrement(ref _currentCount);
                }
            }
            finally
            {
                _lock.ExitWriteLock();
            }
        }
    }
}