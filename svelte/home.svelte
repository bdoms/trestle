<svelte:head>
	<title>Home</title>
</svelte:head>

<h2>Home</h2>

<p>You're logged in as {current_user.email}</p>


<script>
    export let current_user;
</script>
