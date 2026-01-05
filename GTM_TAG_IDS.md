# Google Tag Manager Configuration

## Container ID
**GTM-P5SWCPR7**

## Tags to Configure in GTM Dashboard

### 1. Google Analytics GA4
- **Tag Type:** Google Analytics: GA4 Configuration
- **Measurement ID:** `G-5N6CMNKFPE`
- **Trigger:** All Pages

### 2. Google AdSense (Optional - can also be added via HTML)
- **Tag Type:** Custom HTML
- **HTML Code:**
```html
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-2423510297813794"
     crossorigin="anonymous"></script>
```
- **Trigger:** All Pages

## Implementation Notes
- GTM code has been added to all template files (index, about, privacy, terms, cookies)
- Enzuzo cookie consent banner is retained
- Original Google Analytics and AdSense direct implementations have been removed
- All tags should now be managed through the GTM dashboard at https://tagmanager.google.com
