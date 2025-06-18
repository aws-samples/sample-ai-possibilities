// Table of Contents Generator
(function() {
  'use strict';
  
  // Wait for DOM to be ready
  document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on a page that should have a TOC
    const content = document.querySelector('.content, .main-content');
    if (!content) return;
    
    // Find all headers in the content
    const headers = content.querySelectorAll('h2, h3, h4, h5, h6');
    if (headers.length === 0) return;
    
    // Create TOC container
    const tocContainer = document.createElement('div');
    tocContainer.className = 'toc-container';
    
    const toc = document.createElement('nav');
    toc.className = 'table-of-contents';
    toc.setAttribute('aria-label', 'Table of contents');
    
    const tocTitle = document.createElement('h2');
    tocTitle.className = 'toc-title';
    tocTitle.textContent = 'Table of Contents';
    toc.appendChild(tocTitle);
    
    // Create the list
    const tocList = document.createElement('ul');
    tocList.className = 'toc-list';
    
    let currentLevel = 2;
    let currentList = tocList;
    const listStack = [tocList];
    
    headers.forEach(function(header) {
      const level = parseInt(header.tagName.substring(1));
      const text = header.textContent.trim();
      
      // Generate ID if header doesn't have one
      if (!header.id) {
        header.id = text.toLowerCase()
          .replace(/[^\w\s-]/g, '')
          .replace(/\s+/g, '-');
      }
      
      // Adjust nesting
      while (level > currentLevel) {
        const nestedList = document.createElement('ul');
        nestedList.className = 'toc-nested';
        
        const lastItem = currentList.lastElementChild;
        if (lastItem) {
          lastItem.appendChild(nestedList);
        } else {
          currentList.appendChild(nestedList);
        }
        
        listStack.push(nestedList);
        currentList = nestedList;
        currentLevel++;
      }
      
      while (level < currentLevel && listStack.length > 1) {
        listStack.pop();
        currentList = listStack[listStack.length - 1];
        currentLevel--;
      }
      
      // Create list item
      const listItem = document.createElement('li');
      listItem.className = 'toc-item toc-level-' + level;
      
      const link = document.createElement('a');
      link.href = '#' + header.id;
      link.className = 'toc-link';
      link.textContent = text;
      
      // Smooth scroll
      link.addEventListener('click', function(e) {
        e.preventDefault();
        const target = document.getElementById(header.id);
        if (target) {
          target.scrollIntoView({ behavior: 'smooth', block: 'start' });
          // Update URL without jumping
          history.pushState(null, null, '#' + header.id);
        }
      });
      
      listItem.appendChild(link);
      currentList.appendChild(listItem);
    });
    
    toc.appendChild(tocList);
    tocContainer.appendChild(toc);
    
    // Find the article element and restructure the page
    const article = document.querySelector('article.demo-page, article.experiment-page, article.snippet-page');
    if (article && content) {
      // Create wrapper div
      const wrapper = document.createElement('div');
      wrapper.className = 'content-with-toc';
      
      // Clone the current content
      const mainContent = document.createElement('div');
      mainContent.className = 'main-content';
      
      // Move all content children to mainContent
      while (content.firstChild) {
        mainContent.appendChild(content.firstChild);
      }
      
      // Replace content with new structure
      content.appendChild(wrapper);
      wrapper.appendChild(tocContainer);
      wrapper.appendChild(mainContent);
      
      // Add the content-with-toc class to the wrapper
      content.classList.add('has-toc');
    }
    
    // Highlight current section on scroll
    let ticking = false;
    function updateCurrentSection() {
      const scrollPosition = window.scrollY + 100;
      let currentSection = null;
      
      headers.forEach(function(header) {
        if (header.offsetTop <= scrollPosition) {
          currentSection = header.id;
        }
      });
      
      // Update active link
      document.querySelectorAll('.toc-link').forEach(function(link) {
        link.classList.remove('active');
        if (currentSection && link.getAttribute('href') === '#' + currentSection) {
          link.classList.add('active');
        }
      });
      
      ticking = false;
    }
    
    window.addEventListener('scroll', function() {
      if (!ticking) {
        window.requestAnimationFrame(updateCurrentSection);
        ticking = true;
      }
    });
    
    // Initial update
    updateCurrentSection();
  });
})();