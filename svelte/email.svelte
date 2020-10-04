<svelte:head>
	<title>Change Email</title>
</svelte:head>

<h2>Change Email</h2>

<form action="/account/email?app=1" method="post" on:submit|preventDefault="{changeEmail}">
    <input type="hidden" name="_xsrf"/>

    {#if errors.match}
        <p class="error">Invalid current password. Please try again.</p>
    {/if}
    {#if errors.exists}
        <p class="error">That email address is already in use.</p>
    {/if}

    <p>
        <label for="password">Current Password</label>
        <input type="password" name="password" id="password" required autofocus minlength="8" />
        {#if errors.password}
            <span class="error">Please enter a valid password.</span>
        {/if}
    </p>

    <p>
        <label for="email">Email</label>
        <input type="email" name="email" id="email" required value="{current_user ? current_user.email : ''}"/>
        {#if errors.email}
            <span v-if="errors.email" class="error">Please enter a valid email.</span>
        {/if}
        {#if saved}
            <span class="success">Saved</span>
        {/if}
    </p>

    <p><input type="submit" value="Change Email" /></p>
</form>


<script>
    import utils from './utils';

    export let current_user;

    let errors = {};
    let saved = false;

    let changeEmail = function(e) {
        errors = {};
        saved = false;

        utils.submitForm(this, function(data) {
            saved = true;

            // we want to update the value, but we do not want it to be reactive with the form input
            // that's in case the user never actually submits the form, or there's an error
            current_user.email = document.getElementById('email').value;
        }, function(status, data) {
            errors = data.errors;
        });
    };
</script>
