/*
 * Generate by EnhanceExcel2Anything,don't modify it!
 * Date: 2025-03-08 01:08:38
 * From: A Test.xlsx
*/

namespace EnhanceExcel2Anything
{
    using System.Collections.Generic;
    using UnityEngine;

    public readonly struct ATestSkill
    {
        public int id { get; }
        public ItemType itemType { get; }
        public Vector2 vec2 { get; }
        public Vector3 vec3 { get; }
        public List<CharacterClass> listClass { get; }
        public Dictionary<int, float> mapTest { get; }
        public CharacterClass characterClass { get; }
        
        internal ATestSkill(int id, ItemType itemType, Vector2 vec2, Vector3 vec3, List<CharacterClass> listClass, Dictionary<int, float> mapTest, CharacterClass characterClass)
        {
            this.id = id;
            this.itemType = itemType;
            this.vec2 = vec2;
            this.vec3 = vec3;
            this.listClass = listClass;
            this.mapTest = mapTest;
            this.characterClass = characterClass;
        }
    }
}