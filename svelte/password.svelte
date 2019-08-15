<svelte:head>
	<title>Change Password</title>
</svelte:head>

<h2>Change Password</h2>

<form action="/user/password" method="post" on:submit|preventDefault="{changePassword}">
    <input type="hidden" name="_xsrf"/>

    {#if errors.match}
        <p class="error">Invalid current password. Please try again.</p>
    {/if}

    <p>
        <label for="password">Current Password</label>
        <input type="password" name="password" id="password" required autofocus />
        {#if errors.password}
            <span class="error">Please enter a valid password.</span>
        {/if}
    </p>

    <p>
        <label for="new-password">New Password</label>
        <input type="password" name="new_password" id="new-password" required />
        {#if errors.new_password}
            <span class="error">Please enter a valid password.</span>
        {/if}
        {#if success.ok}
            <span class="success">Saved</span>
        {/if}
    </p>

    <input type="submit" value="Change Password" />
</form>


<script>
    import utils from './utils';

    let errors = {};
    let success = {};

    let changePassword = function(e) {
        utils.submitForm(this, function(error_data, success_data) {
            errors = error_data;
            success = success_data;
        });
    };
</script>
    