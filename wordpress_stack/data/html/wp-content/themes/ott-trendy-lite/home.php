<?php get_header(); ?>
<section class="listing-head">
  <h1>최신 포스트</h1>
  <p>OTT 리뷰를 빠르게 훑어보세요.</p>
</section>

<?php if (have_posts()) : ?>
  <section class="post-grid">
    <?php while (have_posts()) : the_post(); ?>
      <?php get_template_part('template-parts/content', 'card'); ?>
    <?php endwhile; ?>
  </section>
  <?php the_posts_pagination(); ?>
<?php else : ?>
  <p>아직 게시물이 없습니다.</p>
<?php endif; ?>
<?php get_footer(); ?>
