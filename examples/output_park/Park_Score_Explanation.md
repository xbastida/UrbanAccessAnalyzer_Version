# 🌳 Accessibility to Green Spaces
---

## 📖 Overview
This notebook provides a data-driven framework to evaluate **how easily residents can reach green spaces** within a city.

By analyzing the street network and the physical size of parks, we generate an "Accessibility Score" that accounts for both **proximity** and **park size**. Bigger parks tend to have a larger area of influence. 

---

## 📊 Evaluation Criteria: Quality & Proximity

The analysis uses a two-dimensional scoring system to determine the **accessibility** score. We evaluate parks based on their **size** (as a proxy for quality) and their **walk proximity**.


In this notebook PoI quality and distance are discretized manually
### 🌟 Park Quality Scoring
Larger green spaces offer more ecosystem services, biodiversity, and recreational facilities. We categorize OpenStreetMap (OSM) green areas into five quality tiers:

| Score | Min. Area | Classification | Description |
| :--- | :--- | :--- | :--- |
| ⭐⭐⭐⭐⭐ | **250,000 m²** | **Regional Park** | Metropolitan-scale forests or massive parklands. |
| ⭐⭐⭐⭐ | **50,000 m²** | **District Park** | Large parks with diverse sports and social facilities. |
| ⭐⭐⭐ | **10,000 m²** | **Neighborhood Park** | Significant local green spaces with walking paths. |
| ⭐⭐ | **5,000 m²** | **Local Green** | Small parks or large community gardens. |
| ⭐ | **1,000 m²** | **Pocket Park** | Urban squares or small landscaped areas. |


### 👟 Distance Thresholds (Walking Reach)
*   📍 **250m** (~3 min walk): **Excellent Access** — Park acts as an "extended backyard."
*   📍 **500m** (~6 min walk): **Good Access** — Standard urban planning benchmark for health.
*   📍 **750m** (~9 min walk): **Fair Access** — Moderate effort required to reach.
*   📍 **1,000m** (~12 min walk): **Threshold Access** — The limit of comfortable daily walking.

### 💯 Accessibility score 

<html>
<table style="width:100%; border-collapse: collapse; text-align: center;">
<thead>
<tr style="background-color: #f2f2f27b;">
<th style="padding: 10px; border: 1px solid #ddd;">Park Quality / Distance</th>
<th style="padding: 10px; border: 1px solid #ddd;">250m</th>
<th style="padding: 10px; border: 1px solid #ddd;">500m</th>
<th style="padding: 10px; border: 1px solid #ddd;">750m</th>
<th style="padding: 10px; border: 1px solid #ddd;">1000m</th>
</tr>
</thead>
<tbody>
<tr>
<td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">⭐⭐⭐⭐⭐ (5 Stars)</td>
<td style="padding: 10px; border: 1px solid #ddd; background-color: #228B22; color: white;">1.000</td>
<td style="padding: 10px; border: 1px solid #ddd; background-color: #32CD32; color: black;">0.875</td>
<td style="padding: 10px; border: 1px solid #ddd; background-color: #7FFF00; color: black;">0.750</td>
<td style="padding: 10px; border: 1px solid #ddd; background-color: #ADFF2f; color: black;">0.625</td>
</tr>
<tr>
<td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">⭐⭐⭐⭐ (4 Stars)</td>
<td style="padding: 10px; border: 1px solid #ddd; background-color: #32CD32; color: black;">0.875</td>
<td style="padding: 10px; border: 1px solid #ddd; background-color: #7FFF00; color: black;">0.750</td>
<td style="padding: 10px; border: 1px solid #ddd; background-color: #ADFF2f; color: black;">0.625</td>
<td style="padding: 10px; border: 1px solid #ddd; background-color: #FFFF00; color: black;">0.500</td>
</tr>
<tr>
<td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">⭐⭐⭐ (3 Stars)</td>
<td style="padding: 10px; border: 1px solid #ddd; background-color: #7FFF00; color: black;">0.750</td>
<td style="padding: 10px; border: 1px solid #ddd; background-color: #ADFF2f; color: black;">0.625</td>
<td style="padding: 10px; border: 1px solid #ddd; background-color: #FFFF00; color: black;">0.500</td>
<td style="padding: 10px; border: 1px solid #ddd; background-color: #FFD700; color: black;">0.375</td>
</tr>
<tr>
<td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">⭐⭐ (2 Stars)</td>
<td style="padding: 10px; border: 1px solid #ddd; background-color: #ADFF2f; color: black;">0.625</td>
<td style="padding: 10px; border: 1px solid #ddd; background-color: #FFFF00; color: black;">0.500</td>
<td style="padding: 10px; border: 1px solid #ddd; background-color: #FFD700; color: black;">0.375</td>
<td style="padding: 10px; border: 1px solid #ddd; background-color: #FF8C00; color: black;">0.250</td>
</tr>
<tr>
<td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">⭐ (1 Star)</td>
<td style="padding: 10px; border: 1px solid #ddd; background-color: #FFFF00; color: black;">0.500</td>
<td style="padding: 10px; border: 1px solid #ddd; background-color: #FFD700; color: black;">0.375</td>
<td style="padding: 10px; border: 1px solid #ddd; background-color: #FF8C00; color: black;">0.250</td>
<td style="padding: 10px; border: 1px solid #ddd; background-color: #FF4500; color: white;">0.125</td>
</tr>
</tbody>
</table>
</html>

---

> **Note:** Accessibility is only calculated for parks that are **physically reachable**. If a green space is enclosed or has no intersecting pedestrian paths, it is filtered out of the analysis to ensure results reflect real-world utility.

***


***