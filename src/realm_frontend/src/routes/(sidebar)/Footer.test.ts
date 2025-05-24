import { describe, it, expect, beforeEach, vi } from 'vitest';
import Footer from './Footer.svelte';
import { tick } from 'svelte';

/**
 * Simple DOM-based testing helper for Svelte 5
 */
async function renderComponent(Component: any, props = {}) {
  // Create a container for the component
  const container = document.createElement('div');
  document.body.appendChild(container);

  // Create an instance of the component
  const component = new Component({
    target: container,
    props
  });

  // Wait for the component to update
  await tick();

  return {
    container,
    component,
    cleanup: () => {
      component.$destroy();
      document.body.removeChild(container);
    }
  };
}

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
    const { container, cleanup } = await renderComponent(Footer);
    
    // Check if GitHub link is present
    const githubLink = container.querySelector('a[href="https://github.com/smart-social-contracts/realms"]');
    expect(githubLink).not.toBeNull();
    
    cleanup();
  });

  it('displays the commit hash when available', async () => {
    const { container, cleanup } = await renderComponent(Footer);
    
    // Check if commit hash is displayed
    const commitElement = container.querySelector('.text-xs.text-gray-400');
    expect(commitElement?.textContent).toContain('Build: abc1234');
    
    cleanup();
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
    
    const { container, cleanup } = await renderComponent(Footer);
    
    // Check that the commit hash element is not present
    const commitElement = container.querySelector('.text-xs.text-gray-400');
    expect(commitElement).toBeNull();
    
    cleanup();
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
    
    const { container, cleanup } = await renderComponent(Footer);
    
    // Check that the commit hash is truncated
    const commitElement = container.querySelector('.text-xs.text-gray-400');
    expect(commitElement?.textContent).toContain('Build: abcdef1');
    
    cleanup();
  });
});
