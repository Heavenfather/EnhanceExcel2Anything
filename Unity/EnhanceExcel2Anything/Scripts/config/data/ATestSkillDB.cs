/*
 * Generate by EnhanceExcel2Anything,don't modify it!
 * Date: 2025-03-08 01:08:38
 * From: A Test.xlsx
*/

namespace EnhanceExcel2Anything
{
    using System.Collections.Generic;
    using UnityEngine;


    public partial class ATestSkillDB : ConfigBase
    {
        private ATestSkill[] _data;
        private Dictionary<int, int> _idToIdx;
        
        protected override void ConstructConfig()
        {
            _data = new ATestSkill[]
            {
                new(id: 1, vec3: new Vector3(x: 1.33f, y: 3.0f, z: 12.0f), vec2: new Vector2(x: 1.2f, y: 3.0f), itemType: ItemType.WEAPON, characterClass: new CharacterClass(id: 1, base_stats: new List<float>() { 1.3f, 2.1f, 2.0f }, model_path: "assets/res/model/cha1"), listClass: new List<CharacterClass>() { new CharacterClass(id: 1, base_stats: new List<float>() { 1.0f, 2.0f, 3.0f }, model_path: "assets/res/model/cha1"), new CharacterClass(id: 2, base_stats: new List<float>() { 2.0f, 4.0f, 5.0f }, model_path: "assets/res/model/cha1") }, mapTest: new Dictionary<int, float>() { [1] = 22.0f }),
                new(id: 2, vec3: new Vector3(x: 1.33f, y: 3.0f, z: 13.0f), vec2: new Vector2(x: 1.2f, y: 4.0f), itemType: ItemType.WEAPON, characterClass: new CharacterClass(id: 2, base_stats: new List<float>() { 1.3f, 2.1f, 2.0f }, model_path: "assets/res/model/cha1"), listClass: null, mapTest: new Dictionary<int, float>() { [3] = 44.0f, [4] = 22.0f }),
                new(id: 3, vec3: new Vector3(x: 1.33f, y: 3.0f, z: 14.0f), vec2: new Vector2(x: 1.2f, y: 5.0f), itemType: ItemType.WEAPON, characterClass: new CharacterClass(id: 3, base_stats: new List<float>() { 1.3f, 2.1f, 2.0f }, model_path: "assets/res/model/cha1"), listClass: null, mapTest: new Dictionary<int, float>() { [3] = 45.0f, [45] = 55.0f }),
                new(id: 4, vec3: new Vector3(x: 1.33f, y: 3.0f, z: 15.0f), vec2: new Vector2(x: 1.2f, y: 6.0f), itemType: ItemType.ARMOR, characterClass: new CharacterClass(id: 4, base_stats: new List<float>() { 1.3f, 2.1f, 2.0f }, model_path: "assets/res/model/cha1"), listClass: null, mapTest: new Dictionary<int, float>() { [3] = 46.0f, [4] = 4.0f }),
                new(id: 5, vec3: new Vector3(x: 1.33f, y: 3.0f, z: 16.0f), vec2: new Vector2(x: 1.2f, y: 7.0f), itemType: ItemType.ARMOR, characterClass: new CharacterClass(id: 5, base_stats: new List<float>() { 1.3f, 2.1f, 2.0f }, model_path: "assets/res/model/cha1"), listClass: null, mapTest: new Dictionary<int, float>() { [3] = 47.0f }),
                new(id: 8, vec3: new Vector3(x: 1.33f, y: 3.0f, z: 17.0f), vec2: new Vector2(x: 1.2f, y: 8.0f), itemType: ItemType.WEAPON, characterClass: new CharacterClass(id: 6, base_stats: new List<float>() { 1.3f, 2.1f, 2.0f }, model_path: "assets/res/model/cha1"), listClass: null, mapTest: new Dictionary<int, float>() { [3] = 48.0f }),
                new(id: 9, vec3: new Vector3(x: 1.33f, y: 3.0f, z: 18.0f), vec2: new Vector2(x: 1.2f, y: 9.0f), itemType: ItemType.WEAPON, characterClass: new CharacterClass(id: 6, base_stats: new List<float>() { 1.3f, 2.1f, 2.0f }, model_path: "assets/res/model/cha2"), listClass: null, mapTest: new Dictionary<int, float>() { [3] = 49.0f })
            };
            
            MakeIdToIdx();
        }
        
        public ref readonly ATestSkill this[int id]
        {
            get
            {
                TackUsage();
                var ok = _idToIdx.TryGetValue(id, out int idx);
                if (!ok)
                    UnityEngine.Debug.LogError($"[ATestSkill] id: {id} not found");
                return ref _data[idx];
            }
        }
        
        public ATestSkill[] All => _data;
        
        public int Count => _data.Length;
        
        public override void Dispose()
        {
            _data = null;
            OnDispose();
        }
        
        private void MakeIdToIdx()
        {
            _idToIdx = new Dictionary<int,int>(_data.Length);
            for (int i = 0; i < _data.Length; i++)
            {
                _idToIdx[_data[i].id] = i;
            }
        }
    }
}