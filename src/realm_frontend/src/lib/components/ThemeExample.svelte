<!--
  Example Component demonstrating the new theme system usage
  
  This component shows how to use the centralized theme utilities
  instead of hardcoded Tailwind classes.
-->

<script lang="ts">
  import { styles, cn } from '$lib/theme/utilities';
  import { theme } from '$lib/theme/theme';
  
  export let title = 'Theme Example';
  export let variant: 'primary' | 'secondary' | 'success' | 'warning' | 'error' = 'primary';
  export let showCard = true;
  
  // Example of accessing theme values programmatically
  $: primaryColor = theme.colors.primary[600];
  $: fontSize = theme.typography.fontSize.lg;
</script>

<div class={cn(showCard && styles.card.default())}>
  <!-- Example heading using theme utilities -->
  <h2 class={styles.text.heading2()}>
    {title}
  </h2>
  
  <!-- Example body text -->
  <p class={styles.text.body()}>
    This is an example component demonstrating the new centralized theme system. 
    All colors, fonts, and spacing are now controlled from a single configuration file.
  </p>
  
  <!-- Example secondary text -->
  <p class={styles.text.bodySecondary()}>
    Secondary text uses the theme's secondary text color and maintains consistency across the app.
  </p>
  
  <!-- Example buttons using theme utilities -->
  <div class="flex gap-4 mt-6">
    <button class={styles.button.primary()}>
      Primary Button
    </button>
    
    <button class={styles.button.secondary()}>
      Secondary Button
    </button>
    
    <button class={styles.button.success()}>
      Success Button
    </button>
    
    <button class={styles.button.warning()}>
      Warning Button
    </button>
    
    <button class={styles.button.error()}>
      Error Button
    </button>
  </div>
  
  <!-- Example input using theme utilities -->
  <div class="mt-6">
    <label class={styles.text.label()} for="example-input">
      Example Input
    </label>
    <input 
      id="example-input"
      type="text" 
      placeholder="Enter some text..." 
      class={cn(styles.input.default(), 'mt-2 w-full')}
    />
  </div>
  
  <!-- Example alerts -->
  <div class="mt-6 space-y-4">
    <div class={cn(styles.alert.success(), 'p-4')}>
      <strong>Success!</strong> This is a success alert using theme colors.
    </div>
    
    <div class={cn(styles.alert.warning(), 'p-4')}>
      <strong>Warning!</strong> This is a warning alert using theme colors.
    </div>
    
    <div class={cn(styles.alert.error(), 'p-4')}>
      <strong>Error!</strong> This is an error alert using theme colors.
    </div>
    
    <div class={cn(styles.alert.info(), 'p-4')}>
      <strong>Info!</strong> This is an info alert using theme colors.
    </div>
  </div>
  
  <!-- Example of accessing theme values in JavaScript -->
  <div class="mt-6 p-4 border rounded-lg">
    <h3 class={styles.text.heading3()}>Theme Values</h3>
    <p class={styles.text.caption()}>
      Primary color: {primaryColor}<br>
      Font size: {fontSize}<br>
      Current font family: {theme.typography.fontFamily.sans[0]}
    </p>
  </div>
</div>

<style>
  /* Example of using CSS custom properties directly in component styles */
  .custom-element {
    background-color: var(--color-primary-50);
    border: 1px solid var(--color-primary-200);
    border-radius: var(--border-radius-lg);
    padding: var(--spacing-md);
    color: var(--color-text-primary);
    font-family: var(--font-family-sans);
    transition: var(--transition-fast);
  }
  
  .custom-element:hover {
    background-color: var(--color-primary-100);
    border-color: var(--color-primary-300);
  }
</style>
