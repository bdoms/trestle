<svelte:head>
	<title>Change Password</title>
</svelte:head>

<h2>Change Password</h2>

<form action="/account/password?app=1" method="post" on:submit|preventDefault="{changePassword}">
    <input type="hidden" name="_xsrf"/>

    {#if errors.match}
        <p class="error">Invalid current password. Please try again.</p>
    {/if}

    <p>
        <label for="password">Current Password</label>
        <input type="password" name="password" id="password" required autofocus minlength="8" />
        {#if errors.password}
            <span class="error">Please enter a valid password.</span>
        {/if}
    </p>

    <p>
        <label for="new-password">New Password</label>
        <input type="password" name="new_password" id="new-password" required minlength="8" />
        {#if errors.new_password}
            <span class="error">Please enter a valid password.</span>
        {/if}
        {#if saved}
            <span class="success">Saved</span>
        {/if}
    </p>

    <input type="submit" value="Change Password" />
</form>


<script>
    import utils from './utils';

    let errors = {};
    let saved = false;

    let changePassword = function(e) {
        errors = {};
        saved = false;

        utils.submitForm(this, function(data) {
            saved = true;
        }, function(status, data) {
            errors = data.errors;
        });
    };
</script>
