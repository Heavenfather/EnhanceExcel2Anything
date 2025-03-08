using System;
using UnityEngine;

namespace EnhanceExcel2Anything
{
    public class TestReadConfig : MonoBehaviour
    {
        private void Awake()
        {
            LocalizationPool.SwitchLanguage("cn",OnLoadLanguageComplete);
        }

        private void OnLoadLanguageComplete()
        {
            AttribDataDB db = ConfigMemoryPool.Get<AttribDataDB>();
            var config = db[1];
            Debug.Log(config.tipsName);
        }
    }
}