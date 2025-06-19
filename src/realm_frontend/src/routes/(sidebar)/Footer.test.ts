import { describe, it, expect, beforeEach, vi } from 'vitest';
import Footer from './Footer.svelte';
import { mount } from 'svelte';

describe('Footer Component', () => {
  // Set up the document mock before each test
  beforeEach(() => {
    // Mock document.querySelector to return a meta tag with a specific commit hash
    vi.stubGlobal('document', {
      ...document,
      querySelector: vi.fn().mockReturnValue({
        getAttribute: vi.fn().mockReturnValue('abc1234')
      }),
      createElement: document.createElement.bind(document),
      body: document.body
    });
  });

  it('renders GitHub link', async () => {
    const target = document.createElement('div');
    document.body.appendChild(target);
    
    const component = mount(Footer, { target });
    
    // Check if GitHub link is present
    const githubLink = target.querySelector('a[href="https://github.com/smart-social-contracts/realms"]');
    expect(githubLink).not.toBeNull();
    
    component.$destroy();
    document.body.removeChild(target);
  });

  it('displays the commit hash when available', async () => {
    const target = document.createElement('div');
    document.body.appendChild(target);
    
    const component = mount(Footer, { target });
    
    // Check if commit hash is displayed
    const commitElement = target.querySelector('.text-xs.text-gray-400');
    expect(commitElement?.textContent).toContain('(abc1234)');
    
    component.$destroy();
    document.body.removeChild(target);
  });

  it('does not display commit hash and version when it is the placeholder', async () => {
    // Override the mock to return the placeholder value
    vi.stubGlobal('document', {
      ...document,
      querySelector: vi.fn().mockReturnValue({
        getAttribute: vi.fn().mockReturnValue('COMMIT_HASH_PLACEHOLDER')
      }),
      createElement: document.createElement.bind(document),
      body: document.body
    });

    vi.stubGlobal('document', {
      ...document,
      querySelector: vi.fn().mockReturnValue({
        getAttribute: vi.fn().mockReturnValue('VERSION_PLACEHOLDER')
      }),
      createElement: document.createElement.bind(document),
      body: document.body
    });
    
    const target = document.createElement('div');
    document.body.appendChild(target);
    
    const component = mount(Footer, { target });
    
    // Check that the commit hash element is not present
    const commitElement = target.querySelector('.text-xs.text-gray-400');
    expect(commitElement).toBeNull();
    
    component.$destroy();
    document.body.removeChild(target);
  });

  it('formats long commit hashes to 7 characters', async () => {
    // Override the mock to return a long hash
    vi.stubGlobal('document', {
      ...document,
      querySelector: vi.fn().mockReturnValue({
        getAttribute: vi.fn().mockReturnValue('abcdef1234567890')
      }),
      createElement: document.createElement.bind(document),
      body: document.body
    });
    
    const target = document.createElement('div');
    document.body.appendChild(target);
    
    const component = mount(Footer, { target });
    
    // Check that the commit hash is truncated
    const commitElement = target.querySelector('.text-xs.text-gray-400');
    expect(commitElement?.textContent).toContain('(abcdef1)');
    
    component.$destroy();
    document.body.removeChild(target);
  });
});
