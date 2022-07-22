# User Manual

## Compliance Groups

The compliance group feature enables you to prevent users who are not fully compliant - i.e. who have not yet added all their characters to Member Audit - from getting access to a service. This can be an effective incentive for users to add all their characters.

Compliance groups are designated Alliance Auth groups. Users are automatically assigned or removed from these groups depending on their current compliance status.

To require compliance for accessing a service, just add the respective permissions to the compliance groups.

You can define multiple compliance groups. This can be useful if you want to configure individual service access for each state, e.g. by having a compliance group for each state.

The feature is enabled as soon as at least one compliance group exists. Once enabled, a user will be notified when he gains are looses his compliance status. To disable the feature you can either delete all compliance group designations or the compliance groups themselves.

To create a compliance group please follow these steps:

1. Create a new internal group under Group Management / Groups
1. Add the permissions you want to grant to compliant users only
1. Designate that group as compliance group by adding it under Member Audit / Compliance Group Designations

A user is compliant when the following two criteria are both true:

- User has access to Member Audit (i.e. has the access permission)
- User has registered all his characters to Member Audit

```{Note}
Only internal groups can be enabled as compliance groups.
```

```{important}
Once you have enabled a group as compliance group any user assignments will be handled automatically by Member Audit and Alliance Auth.
```
