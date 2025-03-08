using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

namespace EnhanceExcel2Anything
{
    /// <summary>
    /// 多语言版本管理
    /// </summary>
    public static class LocalizationPool
    {
        /// <summary>
        /// 热存池
        /// </summary>
        private static readonly AutoLru<string, string> _cache =
            new AutoLru<string, string>(1000, TimeSpan.FromMinutes(8));

        private static readonly Dictionary<string, string> _allTexts = new Dictionary<string, string>();

        private static string _currentLang = "en";
        private static readonly string _suffix = ".i18n";

        /// <summary>
        /// 切换运行时语言，支持远端下载.在游戏启动或者切换语言时调用
        /// </summary>
        /// <param name="lang"></param>
        /// <param name="onComplete"></param>
        public static void SwitchLanguage(string lang, Action onComplete = null)
        {
            _currentLang = lang;
            LoadLanguage(GetLanguageFilePath(lang), () =>
                CheckLanguagePatch(lang, onComplete));
        }

        /// <summary>
        /// 获取多语言翻译
        /// </summary>
        /// <param name="key"></param>
        /// <returns></returns>
        public static string Get(string key)
        {
            var value = _cache.GetOrAdd(key, () => _allTexts.TryGetValue(key, out string v) ? v : $"#Missing:{key}");
            _cache.MarkUsage(value);
            return value;
        }

        /// <summary>
        /// 加载本地语言文件
        /// </summary>
        /// <param name="path"></param>
        /// <param name="callback"></param>
        private static void LoadLanguage(string path, Action callback)
        {
            // 根据项目实际接入方式实现
            if (File.Exists(path))
            {
                ParseLanguageFile(File.ReadAllText(path), true);
                callback?.Invoke();
            }
            else
            {
                // 不存在在本地，从远端拉取后再解析
                // Downloader.Instance.Download(path, (text) => {
                //     File.WriteAllText(path, text);
                //     ParseLanguageFile(text);
                //     callback?.Invoke();
                // });
            }
        }

        /// <summary>
        /// 解析语言文件
        /// </summary>
        /// <param name="content"></param>
        /// <param name="clearCache"></param>
        private static void ParseLanguageFile(string content, bool clearCache = false)
        {
            // 存在动态切换语言的逻辑，必须先清空之前的缓存
            if (clearCache)
            {
                _allTexts.Clear();
                _cache.Clear();
            }

            foreach (var line in content.Split('\n'))
            {
                var keyValue = line.Split('=');
                if (keyValue.Length == 2)
                {
                    _allTexts[keyValue[0].Trim()] = keyValue[1].Trim();
                }
            }
        }

        /// <summary>
        /// 检测是否有语言补丁
        /// </summary>
        /// <param name="lang"></param>
        /// <param name="callback"></param>
        private static void CheckLanguagePatch(string lang, Action callback)
        {
            // 下载补丁文件 可以按照实际接入方式实现
            string patchPath = $"i18n/patch/{lang}_{DateTime.Now:yy-MM-dd}{_suffix}";
            // Downloader.Instance.CheckFileExists(deltaPath, exists => {
            //     if (exists)
            //     {
            //         Downloader.Instance.Download(deltaPath, deltaContent => {
            //             ParseLanguageFile(deltaContent);
            //             callback?.Invoke();
            //         });
            //     }
            //     else
            //     {
            //         callback?.Invoke();
            //     }
            // });
            callback?.Invoke();
        }

        /// <summary>
        /// 获取本地语言文件路径
        /// </summary>
        /// <param name="lang"></param>
        /// <returns></returns>
        private static string GetLanguageFilePath(string lang)
        {
            // 按照实际项目接入修改
            return Path.Combine(Application.streamingAssetsPath, $"i18n/master_{lang}{_suffix}");
        }
    }
}