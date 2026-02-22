<?php get_header(); ?>
<?php if (have_posts()) : while (have_posts()) : the_post(); ?>
  <article class="single-card">
    <header class="single-head">
      <h1><?php the_title(); ?></h1>
      <p class="meta"><?php echo esc_html(get_the_date('Y.m.d')); ?></p>
    </header>

    <?php if (has_post_thumbnail()) : ?>
      <figure class="single-thumb"><?php the_post_thumbnail('large'); ?></figure>
    <?php endif; ?>

    <div class="single-content"><?php the_content(); ?></div>

    <footer class="single-foot">
      <?php $tags = get_the_tags(); ?>
      <?php if ($tags && !is_wp_error($tags)) : ?>
        <div class="tag-list" aria-label="Post tags">
          <?php foreach ($tags as $tag) : ?>
            <a class="tag-pill" href="<?php echo esc_url(get_tag_link($tag->term_id)); ?>">
              #<?php echo esc_html($tag->name); ?>
            </a>
          <?php endforeach; ?>
        </div>
      <?php endif; ?>
    </footer>
  </article>

  <section class="comments-wrap">
    <?php comments_template(); ?>
  </section>
<?php endwhile; endif; ?>
<?php get_footer(); ?>
