using System;

namespace EnhanceExcel2Anything
{
    /// <summary>
    /// 所有配置对象缓存池
    /// 统一获取统一管理配置对象，方便动态释放
    /// </summary>
    public static class ConfigMemoryPool
    {
        //最大保留50份配置，可以按照具体的配置体量调整，每10分钟清理一次
        private static readonly AutoLru<string, ConfigBase> _configPool = new AutoLru<string, ConfigBase>(50, TimeSpan.FromMinutes(10));

        public static T Get<T>() where T : ConfigBase, new()
        {
            var key = typeof(T).FullName;
            return (T)_configPool.GetOrAdd(key, () => new T());
        }
        
        public static bool TryGet<T>(out T config) where T : ConfigBase, new()
        {
            try
            {
                config = Get<T>();
                return true;
            }
            catch (InvalidOperationException ex) when (ex.Message.Contains("full"))
            {
                //紧急扩容
                config = new T();
                return true;
            }
            catch
            {
                config = default;
                return false;
            }
        }

        internal static void MarkUsage(ConfigBase config)
        {
            _configPool.MarkUsage(config);
        }
    }
}