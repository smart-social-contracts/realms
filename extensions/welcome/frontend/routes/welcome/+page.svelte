<script>
  import { onMount } from 'svelte';
  import { browser } from '$app/environment';
  
  let isMobile = false;
  let currentPhotoIndex = 0;
  
  // Available photos
  const photos = [
    '/photos/Luzern.jpg',
    '/photos/Zürich.jpg'
  ];
  
  // Check for mobile viewport and setup photo carousel
  onMount(() => {
    if (browser) {
      const checkMobile = () => {
        isMobile = window.innerWidth < 768;
      };
      
      // Initial check
      checkMobile();
      
      // Add resize listener
      window.addEventListener('resize', checkMobile);
      
      // Setup photo carousel - change every 5 seconds
      const photoInterval = setInterval(() => {
        currentPhotoIndex = (currentPhotoIndex + 1) % photos.length;
      }, 5000);
      
      // Cleanup
      return () => {
        window.removeEventListener('resize', checkMobile);
        clearInterval(photoInterval);
      };
    }
  });
</script>

<svelte:head>
  <title>Welcome</title>
</svelte:head>

<div class="welcome-container">
  {#if browser}
    <div class="background-photo-container">
      {#each photos as photo, index}
        <img
          src={photo}
          alt="Background {index + 1}"
          class="background-photo {index === currentPhotoIndex ? 'active' : ''}"
        />
      {/each}
    </div>
    <!-- Photo filename display -->
    <div class="photo-info">
      {photos[currentPhotoIndex].split('/').pop().replace('.jpg', '')}
    </div>
    
    <!-- "Built with" text -->
    <div class="built-with-love">
      <a href="https://internetcomputer.org" target="_blank" rel="noopener noreferrer" class="built-with-link">
        Built on the 
        <img src="/images/internet-computer-icp-logo.svg" alt="Internet Computer Logo" width="20" height="20" class="inline-logo" />
        with ❤️ from 🇨🇭
      </a>
    </div>
  {/if}
  
  <div class="content">
    <div class="hero-text">
      <h1>Realms GOS - The Governance Operating System</h1>
      <p class="hero-subtitle">Fully auditable. Fully transparent. AI-powered.</p>
      <p class="hero-subtitle">Engineered to eliminate corruption and inefficiencies.</p>
      <!-- <p class="hero-subtitle">Create a complete ready-to-use public administration in seconds.</p> -->
    </div>
    
    <div class="button-container">
      <a href="/app/visitor" class="btn btn-visitor">
        Try the sandbox
      </a>
    </div>
  </div>
  
  <!-- Scroll indicator -->
  <div class="scroll-indicator">
    <!-- <div class="scroll-text">Scroll to learn more</div> -->
    <div class="scroll-arrow">
      <div class="arrow-down"></div>
    </div>
  </div>
</div>

<!-- Our Mission Section -->
<section class="mission-section">
  <div class="mission-content">
    <h2>Our mission</h2>
    <p>We are the Open Governance Foundation, a Switzerland-based non-profit dedicated to promote the development of decentralized technology to create transparent, efficient, and innovative governance systems, fostering better governance practices worldwide.</p>
    <button class="read-more-btn">Read More</button>
  </div>
  <div class="mission-image">
    <!-- Placeholder for image -->
  </div>
</section>

<!-- Our Founding Values Section -->
<section class="values-section">
  <div class="values-container">
    <h2>Our founding values</h2>
    
    <div class="values-grid">
      <div class="value-item">
        <div class="value-number">01</div>
        <h3>Transparency</h3>
        <p>Transparency builds trust between the government and the public, as users can see how processes are executed and where resources, such as tax money, are allocated. Transparency also helps prevent corruption and strengthens the legitimacy of institutions.</p>
      </div>
      
      <div class="value-item">
        <div class="value-number">02</div>
        <h3>Efficiency</h3>
        <p>Efficiency involves delivering services effectively while minimizing costs and reducing waste. This fosters a strong sense of fairness, reinforcing public confidence in the governance system. As a result, users are more likely to support and comply with tax obligations, reducing tax evasion and promoting greater civic responsibility.</p>
      </div>
      
      <div class="value-item">
        <div class="value-number">03</div>
        <h3>Diversity</h3>
        <p>Diversity in governance ensures that a wide range of perspectives are represented. This leads to more inclusive and equitable policies that cater to different societal needs, fostering social cohesion and reducing marginalization.</p>
      </div>
      
      <div class="value-item">
        <div class="value-number">04</div>
        <h3>Resilience</h3>
        <p>Resilience enables governance systems to respond to crises, adapt to changes, and recover from setbacks, such as economic shocks or natural disasters. A resilient governance system ensures stability and continuity, even in times of stress, protecting long-term societal wellbeing.</p>
      </div>
    </div>
  </div>
</section>

<style>
  .welcome-container {
    position: relative;
    width: 100%;
    height: 100vh;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .background-photo-container {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: -2;
  }
  
  .background-photo {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    opacity: 0;
    transition: opacity 1s ease-in-out;
  }
  
  .background-photo.active {
    opacity: 1;
  }
  
  .photo-info {
    position: absolute;
    bottom: 1rem;
    left: 1rem;
    color: white;
    font-size: 0.9rem;
    font-weight: 400;
    text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.7);
    z-index: 1;
    background-color: rgba(0, 0, 0, 0.3);
    padding: 0.5rem 0.8rem;
    border-radius: 4px;
    backdrop-filter: blur(4px);
  }
  
  .built-with-love {
    position: absolute;
    bottom: 1rem;
    right: 1rem;
    color: white;
    font-size: 0.9rem;
    font-weight: 400;
    text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.7);
    z-index: 1;
    background-color: rgba(0, 0, 0, 0.3);
    padding: 0.5rem 0.8rem;
    border-radius: 4px;
    backdrop-filter: blur(4px);
  }
  
  .built-with-link {
    color: white;
    text-decoration: none;
    display: flex;
    align-items: center;
    gap: 0.2rem;
  }
  
  .built-with-link:hover {
    color: rgba(255, 255, 255, 0.8);
    text-decoration: none;
  }
  
  .inline-logo {
    display: inline-block;
    vertical-align: middle;
    margin: 0 0.2rem;
  }

  .content {
    position: relative;
    z-index: 1;
    text-align: center;
    color: #ffffff;
    padding: 2rem;
    display: flex;
    flex-direction: column;
    align-items: center;
    background-color: rgba(0, 0, 0, 0.6);
    backdrop-filter: blur(8px);
    border-radius: 12px;
    margin: 2rem;
  }
  
  /* Desktop layout - content on the right */
  @media (min-width: 768px) {
    .content {
      position: absolute;
      right: 0;
      top: 50%;
      transform: translateY(-50%);
      width: 50%;
      max-width: 600px;
      padding: 3rem;
      align-items: flex-start;
      text-align: left;
      background-color: rgba(0, 0, 0, 0.6);
      backdrop-filter: blur(8px);
      border-radius: 12px;
      margin-right: 2rem;
    }
  }

  .hero-text {
    text-align: center;
    margin-bottom: 2rem;
  }
  
  /* Desktop hero text alignment */
  @media (min-width: 768px) {
    .hero-text {
      text-align: left;
    }
  }
  
  h1 {
    font-size: 2.8rem;
    margin-bottom: 1.5rem;
    text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
    line-height: 1.2;
    font-weight: 600;
  }
  
  .hero-subtitle {
    font-size: 1.3rem;
    margin-bottom: 0.5rem;
    text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
    font-weight: 400;
    opacity: 0.95;
  }
  
  .button-container {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    margin-top: 1rem;
    width: 100%;
    max-width: 300px;
  }
  
  .btn {
    display: inline-block;
    padding: 1rem 1.5rem;
    text-decoration: none;
    border-radius: 30px;
    font-weight: 600;
    transition: all 0.3s ease;
    text-align: center;
    letter-spacing: 0.5px;
  }
  
  .btn-member {
    background-color: rgba(59, 130, 246, 0.8);
    color: white;
    border: 2px solid rgba(59, 130, 246, 0.9);
  }
  
  .btn-member:hover {
    background-color: rgba(59, 130, 246, 1);
    transform: translateY(-2px);
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
  }
  
  .btn-visitor {
    background-color: transparent;
    color: white;
    border: 2px solid rgba(255, 255, 255, 0.6);
  }
  
  .btn-visitor:hover {
    background-color: rgba(255, 255, 255, 0.1);
    border-color: rgba(255, 255, 255, 0.8);
    transform: translateY(-2px);
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
  }
  
  /* Scroll indicator styles */
  .scroll-indicator {
    position: absolute;
    bottom: 2rem;
    left: 50%;
    transform: translateX(-50%);
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
    z-index: 2;
    animation: fadeInUp 2s ease-out 1s both;
  }
  
  .scroll-text {
    color: rgba(255, 255, 255, 0.8);
    font-size: 0.9rem;
    font-weight: 400;
    text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
    letter-spacing: 0.5px;
  }
  
  .scroll-arrow {
    display: flex;
    justify-content: center;
    align-items: center;
    animation: bounce 2s infinite;
  }
  
  .arrow-down {
    width: 0;
    height: 0;
    border-left: 8px solid transparent;
    border-right: 8px solid transparent;
    border-top: 12px solid rgba(255, 255, 255, 0.8);
    filter: drop-shadow(1px 1px 2px rgba(0, 0, 0, 0.5));
  }
  
  @keyframes bounce {
    0%, 20%, 50%, 80%, 100% {
      transform: translateY(0);
    }
    40% {
      transform: translateY(-8px);
    }
    60% {
      transform: translateY(-4px);
    }
  }
  
  @keyframes fadeInUp {
    from {
      opacity: 0;
      transform: translateX(-50%) translateY(20px);
    }
    to {
      opacity: 1;
      transform: translateX(-50%) translateY(0);
    }
  }
  
  /* Mission Section Styles */
  .mission-section {
    display: flex;
    align-items: center;
    min-height: 60vh;
    padding: 4rem 2rem;
    background-color: #f8f9fa;
    gap: 4rem;
  }
  
  .mission-content {
    flex: 1;
    max-width: 600px;
  }
  
  .mission-content h2 {
    font-size: 2.5rem;
    font-weight: 400;
    color: #333;
    margin-bottom: 2rem;
    line-height: 1.2;
  }
  
  .mission-content p {
    font-size: 1.1rem;
    line-height: 1.6;
    color: #555;
    margin-bottom: 2rem;
  }
  
  .read-more-btn {
    background-color: #333;
    color: white;
    border: none;
    padding: 0.8rem 2rem;
    font-size: 1rem;
    font-weight: 500;
    cursor: pointer;
    transition: background-color 0.3s ease;
  }
  
  .read-more-btn:hover {
    background-color: #555;
  }
  
  .mission-image {
    flex: 1;
    min-height: 300px;
    background-color: #e9ecef;
    border-radius: 8px;
  }
  
  /* Values Section Styles */
  .values-section {
    padding: 5rem 2rem;
    background-color: white;
  }
  
  .values-container {
    max-width: 1200px;
    margin: 0 auto;
  }
  
  .values-container h2 {
    font-size: 2.5rem;
    font-weight: 400;
    color: #333;
    text-align: center;
    margin-bottom: 4rem;
    line-height: 1.2;
  }
  
  .values-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 3rem;
  }
  
  .value-item {
    padding: 2rem;
    background-color: #f8f9fa;
    border-radius: 8px;
  }
  
  .value-number {
    font-size: 1.2rem;
    font-weight: 600;
    color: #666;
    margin-bottom: 1rem;
  }
  
  .value-item h3 {
    font-size: 1.5rem;
    font-weight: 600;
    color: #333;
    margin-bottom: 1rem;
    line-height: 1.3;
  }
  
  .value-item p {
    font-size: 1rem;
    line-height: 1.6;
    color: #555;
  }
  
  /* For mobile screens */
  @media (max-width: 767px) {
    h1 {
      font-size: 1.8rem;
      margin-bottom: 1rem;
    }
    
    .hero-subtitle {
      font-size: 1.1rem;
      margin-bottom: 0.4rem;
    }
    
    .hero-text {
      margin-bottom: 1.5rem;
    }
    
    .button-container {
      max-width: 250px;
    }
    
    .btn {
      padding: 0.8rem 1.2rem;
    }
    
    /* Adjust positioning for mobile to avoid overlap */
    .built-with-love {
      bottom: 4rem; /* Move higher to avoid arrow overlap */
      right: 0.5rem;
      font-size: 0.8rem;
      padding: 0.4rem 0.6rem;
    }
    
    .photo-info {
      bottom: 4rem; /* Move higher to match built-with text */
      left: 0.5rem;
      font-size: 0.8rem;
      padding: 0.4rem 0.6rem;
    }
    
    .scroll-indicator {
      bottom: 1rem; /* Keep arrow at bottom */
    }
    
    /* Mission section mobile */
    .mission-section {
      flex-direction: column;
      padding: 3rem 1rem;
      gap: 2rem;
      min-height: auto;
    }
    
    .mission-content h2 {
      font-size: 2rem;
      margin-bottom: 1.5rem;
    }
    
    .mission-content p {
      font-size: 1rem;
    }
    
    .mission-image {
      min-height: 200px;
    }
    
    /* Values section mobile */
    .values-section {
      padding: 3rem 1rem;
    }
    
    .values-container h2 {
      font-size: 2rem;
      margin-bottom: 3rem;
    }
    
    .values-grid {
      grid-template-columns: 1fr;
      gap: 2rem;
    }
    
    .value-item {
      padding: 1.5rem;
    }
    
    .value-item h3 {
      font-size: 1.3rem;
    }
    
    .scroll-indicator {
      bottom: 1rem;
    }
    
    .scroll-text {
      font-size: 0.8rem;
    }
  }
</style>
