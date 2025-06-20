#!/usr/bin/env python3
"""
Test script to verify substring matching functionality
"""

def matches_includes(tags, include_rules):
    """Test version of matches_includes function"""
    tag_map = {t["Key"].lower(): t.get("Value", "").lower() for t in tags}
    for cond in include_rules:
        key = cond["Key"].lower()
        val = tag_map.get(key)
        if val:
            if "Values" in cond:
                match_type = cond.get("MatchType", "exact").lower()
                
                if match_type == "contains":
                    # Substring matching
                    for target_val in cond["Values"]:
                        if target_val.lower() in val:
                            return True
                else:
                    # Default exact matching
                    if val in [v.lower() for v in cond["Values"]]:
                        return True
            else:
                return True
    return False

def test_substring_matching():
    """Test the substring matching functionality"""
    print("Testing substring matching functionality...\n")
    
    # Test data - simulating AWS resource tags
    test_resources = [
        {"tags": [{"Key": "Name", "Value": "nef-jenkins-master"}], "expected": True},
        {"tags": [{"Key": "Name", "Value": "my-nef-jenkins-slave"}], "expected": True},
        {"tags": [{"Key": "Name", "Value": "jenkins-build-server"}], "expected": False},  # 'nef-jenkins' not in 'jenkins-build-server'
        {"tags": [{"Key": "Name", "Value": "web-server-01"}], "expected": False},
        {"tags": [{"Key": "Name", "Value": "database-server"}], "expected": False},
        {"tags": [{"Key": "Name", "Value": "NEF-JENKINS-PROD"}], "expected": True},  # Case insensitive
        {"tags": [{"Key": "Name", "Value": "prod-nef-jenkins-01"}], "expected": True},  # Additional test
    ]
    
    # Test rule with substring matching
    nabserv_rule = [{"Key": "Name", "Values": ["nef-jenkins"], "MatchType": "contains"}]
    
    print("Testing 'nabserv' rule with substring matching:")
    print(f"Rule: {nabserv_rule[0]}\n")
    
    all_passed = True
    for i, resource in enumerate(test_resources, 1):
        result = matches_includes(resource["tags"], nabserv_rule)
        status = "✅ PASS" if result == resource["expected"] else "❌ FAIL"
        
        print(f"Test {i}: {resource['tags'][0]['Value']}")
        print(f"  Expected: {resource['expected']}, Got: {result} {status}")
        
        if result != resource["expected"]:
            all_passed = False
    
    print(f"\n{'='*50}")
    if all_passed:
        print("🎉 All tests PASSED! Substring matching is working correctly.")
    else:
        print("❌ Some tests FAILED. Please check the implementation.")
    
    # Test exact matching for comparison
    print(f"\n{'='*50}")
    print("Testing exact matching for comparison:")
    exact_rule = [{"Key": "Name", "Values": ["nef-jenkins-master"], "MatchType": "exact"}]
    print(f"Rule: {exact_rule[0]}\n")
    
    for i, resource in enumerate(test_resources, 1):
        result = matches_includes(resource["tags"], exact_rule)
        expected_exact = resource["tags"][0]["Value"].lower() == "nef-jenkins-master"
        status = "✅ PASS" if result == expected_exact else "❌ FAIL"
        
        print(f"Test {i}: {resource['tags'][0]['Value']}")
        print(f"  Expected: {expected_exact}, Got: {result} {status}")

if __name__ == "__main__":
    test_substring_matching()