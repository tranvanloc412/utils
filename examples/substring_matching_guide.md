# Substring Matching Guide

This guide explains how to use the enhanced tag matching functionality that supports both exact and substring matching.

## Overview

The `matches_includes` and `matches_excludes` functions now support two matching types:
- **Exact matching** (default for includes)
- **Substring matching** (default for excludes, available for includes)

## Configuration Format

### Basic Structure
```python
{
    "Key": "tag_key_name",
    "Values": ["value1", "value2"],
    "MatchType": "exact" | "contains"  # Optional
}
```

## Examples

### 1. Exact Matching (Default for Includes)
```python
# This will match resources where Environment tag equals exactly "Production"
{
    "Key": "Environment",
    "Values": ["Production"]
    # MatchType defaults to "exact" for includes
}
```

**Matches:**
- `Environment: "Production"` ✅
- `Environment: "production"` ✅ (case-insensitive)

**Does NOT match:**
- `Environment: "Production-East"` ❌
- `Environment: "Pre-Production"` ❌

### 2. Substring Matching for Includes
```python
# This will match resources where Name tag contains "jenkins"
{
    "Key": "Name",
    "Values": ["jenkins"],
    "MatchType": "contains"
}
```

**Matches:**
- `Name: "nef-jenkins-master"` ✅
- `Name: "jenkins-slave-01"` ✅
- `Name: "my-jenkins-server"` ✅

**Does NOT match:**
- `Name: "build-server"` ❌
- `Name: "jenkin"` ❌ (partial word)

### 3. Substring Matching for Excludes (Default)
```python
# This will exclude resources where Name contains "nef-jenkins"
{
    "Key": "Name",
    "Values": ["nef-jenkins"]
    # MatchType defaults to "contains" for excludes
}
```

**Excludes:**
- `Name: "nef-jenkins-master"` ✅
- `Name: "my-nef-jenkins-01"` ✅
- `Name: "nef-jenkins"` ✅

### 4. Exact Matching for Excludes
```python
# This will exclude resources where Environment equals exactly "Test"
{
    "Key": "Environment",
    "Values": ["Test"],
    "MatchType": "exact"
}
```

**Excludes:**
- `Environment: "Test"` ✅
- `Environment: "test"` ✅ (case-insensitive)

**Does NOT exclude:**
- `Environment: "Testing"` ❌
- `Environment: "Pre-Test"` ❌

## Updated TAG_PRESETS Example

```python
TAG_PRESETS = {
    # Exact matching (default for includes)
    "managed_by_cms": [{"Key": "managed_by", "Values": ["CMS"]}],
    
    # Substring matching for includes
    "jenkins_servers": [{"Key": "Name", "Values": ["jenkins"], "MatchType": "contains"}],
    
    # Substring matching for excludes (default behavior)
    "nabserv": [{"Key": "Name", "Values": ["nef-jenkins"]}],
    
    # Exact matching for excludes
    "test_env_exact": [{"Key": "Environment", "Values": ["Test"], "MatchType": "exact"}],
}
```

## Use Cases

### When to Use Exact Matching
- **Environment tags**: `Production`, `Development`, `Staging`
- **Boolean flags**: `Yes`, `No`, `true`, `false`
- **Specific identifiers**: Account IDs, specific application names

### When to Use Substring Matching
- **Server naming patterns**: `jenkins`, `web-server`, `database`
- **Application prefixes**: `nef-`, `cms-`, `app-`
- **Partial identifiers**: When you want to match multiple variations

## Migration Notes

- **Backward Compatibility**: Existing configurations continue to work
- **Default Behavior**: 
  - Includes: Exact matching (safer, more precise)
  - Excludes: Substring matching (maintains existing behavior)
- **Explicit Control**: Add `"MatchType"` to override defaults