---
layout: home
title: Home
nav_order: 1
description: "AI Possibilities Samples: AWS AI/ML demos, experiments and code snippets."
permalink: /
---

<!-- --- Add this section to merge the README here

{% include_relative README.md %} -->

---

## Explore Our Content

<section class="section-block">
  <h2>Latest Demos</h2>
  <div class="content-grid">
    {% for demo in site.demos limit:3 %}
      <div class="content-card">
        <h3><a href="{{ demo.url | relative_url }}">{{ demo.title }}</a></h3>
        <p>{{ demo.description }}</p>
      </div>
    {% endfor %}
  </div>
</section>

<section class="section-block">
  <h2>Recent Experiments</h2>
  <div class="content-grid">
    {% for experiment in site.experiments limit:3 %}
      <div class="content-card">
        <h3><a href="{{ experiment.url | relative_url }}">{{ experiment.title }}</a></h3>
        <p>{{ experiment.description }}</p>
      </div>
    {% endfor %}
  </div>
</section>

<section class="section-block">
  <h2>Recent Snippets</h2>
  <div class="content-grid">
    {% for snippet in site.snippets limit:3 %}
      <div class="content-card">
        <h3><a href="{{ snippet.url | relative_url }}">{{ snippet.title }}</a></h3>
        <p>{{ snippet.description }}</p>
      </div>
    {% endfor %}
  </div>
</section>
---
[View All Demos]({{ '/demos/' | relative_url }}){: .btn .btn-primary }
[View All Experiments]({{ '/experiments/' | relative_url }}){: .btn .btn-secondary }
[View All Snippets]({{ '/snippets/' | relative_url }}){: .btn .btn-secondary }

[View on GitHub](https://github.com/aws-samples/sample-ai-possibilities){: .btn .btn-secondary }