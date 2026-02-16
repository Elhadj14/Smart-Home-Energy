"""
Model Features Inspector
========================
يفحص نماذجك ويعطيك قائمة كاملة بالـ features المطلوبة
"""

import joblib
import json

# ============================================================================
# ضع مسار نماذجك هنا
# ============================================================================

PV_MODEL_PATH = 'pv_power_model_ultra.pkl'
CONSUMPTION_MODEL_PATH = 'consumption_hourly_model.pkl'

# ============================================================================


def inspect_model(model_path, model_name):
    """فحص نموذج واستخراج معلوماته"""
    print("\n" + "="*70)
    print(f"Inspecting: {model_name}")
    print("="*70)
    
    # تحميل النموذج
    model_data = joblib.load(model_path)
    
    print(f"\n📦 Model Type: {type(model_data)}")
    
    if isinstance(model_data, dict):
        print(f"\n📋 Dictionary Keys:")
        for key in model_data.keys():
            print(f"   - {key}")
        
        # استخراج Features
        if 'features' in model_data:
            features = model_data['features']
            print(f"\n✅ Features Found ({len(features)} total):")
            print("-"*70)
            for i, feature in enumerate(features, 1):
                print(f"{i:3d}. {feature}")
            
            # حفظ في ملف
            output_file = f"{model_name.replace(' ', '_')}_features.txt"
            with open(output_file, 'w') as f:
                f.write(f"Features for {model_name}\n")
                f.write("="*70 + "\n\n")
                for i, feature in enumerate(features, 1):
                    f.write(f"{i}. {feature}\n")
            
            print(f"\n💾 Saved to: {output_file}")
            
            return features
        else:
            print("\n⚠️  'features' key not found in dictionary")
            
            # جرّب استخراج من النموذج مباشرة
            if 'models' in model_data:
                models = model_data['models']
                if isinstance(models, dict):
                    first_model = list(models.values())[0]
                    if hasattr(first_model, 'feature_names_in_'):
                        features = list(first_model.feature_names_in_)
                        print(f"\n✅ Extracted from model.feature_names_in_ ({len(features)} total):")
                        print("-"*70)
                        for i, feature in enumerate(features, 1):
                            print(f"{i:3d}. {feature}")
                        
                        # حفظ
                        output_file = f"{model_name.replace(' ', '_')}_features.txt"
                        with open(output_file, 'w') as f:
                            f.write(f"Features for {model_name}\n")
                            f.write("="*70 + "\n\n")
                            for i, feature in enumerate(features, 1):
                                f.write(f"{i}. {feature}\n")
                        
                        print(f"\n💾 Saved to: {output_file}")
                        return features
        
        # معلومات إضافية
        if 'best_model_name' in model_data:
            print(f"\n🏆 Best Model: {model_data['best_model_name']}")
        
        if 'metrics' in model_data:
            print(f"\n📊 Metrics:")
            metrics = model_data['metrics']
            if isinstance(metrics, dict):
                for key, value in metrics.items():
                    print(f"   {key}: {value}")
        
        if 'target' in model_data:
            print(f"\n🎯 Target Variable: {model_data['target']}")
        
        if 'scaler' in model_data:
            print(f"\n⚖️  Scaler: {type(model_data['scaler']).__name__}")
    
    else:
        # نموذج مباشر
        if hasattr(model_data, 'feature_names_in_'):
            features = list(model_data.feature_names_in_)
            print(f"\n✅ Features ({len(features)} total):")
            print("-"*70)
            for i, feature in enumerate(features, 1):
                print(f"{i:3d}. {feature}")
            
            # حفظ
            output_file = f"{model_name.replace(' ', '_')}_features.txt"
            with open(output_file, 'w') as f:
                f.write(f"Features for {model_name}\n")
                f.write("="*70 + "\n\n")
                for i, feature in enumerate(features, 1):
                    f.write(f"{i}. {feature}\n")
            
            print(f"\n💾 Saved to: {output_file}")
            return features
    
    return None


def create_feature_mapping():
    """إنشاء ملف mapping للـ features"""
    print("\n" + "="*70)
    print("Creating Feature Mapping Template")
    print("="*70)
    
    mapping_template = """
# Feature Mapping Guide
# =====================
# استخدم هذا الملف لإنشاء features مفقودة

# مثال:
# إذا نموذجك يحتاج: 'AirTemperature'
# وعندك: 'temperature'
# أضف:
# features['AirTemperature'] = temperature

# PV Model Features Mapping
# -------------------------
# AirMass = ؟
# AirPressure = ؟
# AirTemperature = temperature
# DayOfWeek = day_of_week
# DayOfWeek_cos = cos(2 * pi * day_of_week / 7)
# DayOfWeek_sin = sin(2 * pi * day_of_week / 7)
# ... (أكمل البقية)

# Consumption Model Features Mapping
# ----------------------------------
# ChangeRate_1h = (current_consumption - consumption_1h_ago) / consumption_1h_ago
# Consumption_Delta1h = current_consumption - consumption_1h_ago
# Consumption_Delta24h = current_consumption - consumption_24h_ago
# ... (أكمل البقية)
"""
    
    with open('feature_mapping_template.txt', 'w') as f:
        f.write(mapping_template)
    
    print("✅ Created: feature_mapping_template.txt")
    print("   Edit this file to map your features")


def main():
    """البرنامج الرئيسي"""
    print("\n" + "="*70)
    print("MODEL FEATURES INSPECTOR")
    print("="*70)
    print("\nThis script will:")
    print("1. Load your models")
    print("2. Extract required features")
    print("3. Save them to text files")
    print("="*70)
    
    # فحص PV Model
    pv_features = inspect_model(PV_MODEL_PATH, "PV Power Model")
    
    # فحص Consumption Model
    cons_features = inspect_model(CONSUMPTION_MODEL_PATH, "Consumption Model")
    
    # إنشاء template
    create_feature_mapping()
    
    # ملخص
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    if pv_features:
        print(f"\n✅ PV Model: {len(pv_features)} features")
        print(f"   Saved to: PV_Power_Model_features.txt")
    else:
        print(f"\n⚠️  PV Model: Could not extract features")
    
    if cons_features:
        print(f"\n✅ Consumption Model: {len(cons_features)} features")
        print(f"   Saved to: Consumption_Model_features.txt")
    else:
        print(f"\n⚠️  Consumption Model: Could not extract features")
    
    print("\n📝 Next Steps:")
    print("   1. Open the generated .txt files")
    print("   2. Check what features are needed")
    print("   3. Share them with me")
    print("   4. I'll create the correct feature engineering code")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    main()
