# Operational runbooks

## Deployment does not reconcile

```bash
flux get all -A
flux logs --all-namespaces --level=error
kubectl get kustomizations -A
kubectl get helmreleases -A
```

Check for:

- invalid manifests;
- unreachable Helm repository;
- missing CRDs;
- missing Secrets;
- image pull failures;
- dependency ordering.

## Pod is CrashLoopBackOff

```bash
kubectl describe pod <pod> -n <namespace>
kubectl logs <pod> -n <namespace>
kubectl logs <pod> -n <namespace> --previous
```

Common causes:

- missing Secret key;
- incorrect connection string;
- database migration failure;
- incompatible image;
- invalid health endpoint;
- insufficient memory.

## PVC is Pending

```bash
kubectl describe pvc <pvc> -n <namespace>
kubectl get storageclass
kubectl get pods -n kube-system | grep local-path
```

For this single-node design, the expected storage class is `local-path`.

## Certificate is not issued

```bash
kubectl describe certificate <name> -n <namespace>
kubectl get challenges,orders -A
kubectl logs -n cert-manager deploy/cert-manager
```

Verify:

- DNS points to the VPS;
- ports 80 and 443 are reachable;
- Traefik ingress class exists;
- ACME email and ClusterIssuer are correct.

## Backup Job failed

```bash
kubectl get jobs -n data
kubectl describe job <job> -n data
kubectl logs job/<job> -n data
```

Verify:

- backup PVC is bound;
- enough free disk space exists;
- source database is reachable;
- credentials are correct;
- backup format is supported by the running image.

## Node disk pressure

```bash
kubectl describe node
df -h
sudo du -xhd1 /var/lib/rancher/k3s
sudo du -xhd1 /var/lib/rancher/k3s/storage
```

Do not delete PVC directories manually while workloads are running.

Possible remediation:

- remove expired backups;
- reduce telemetry retention;
- expand the VPS disk;
- move backups off-site;
- identify runaway logs.

## Node memory pressure

```bash
kubectl top nodes
kubectl top pods -A --sort-by=memory
```

Reduce workload concurrency or limits only after identifying the consumer.
ClickHouse, Tempo and Grafana are likely high-memory components.

## Emergency application stop

Scale application deployments to zero while preserving data services:

```bash
kubectl scale deployment --all   -n casinoshiz   --replicas=0
```

Reconcile Git before relying on this as a lasting state, otherwise Flux may
restore the declared replica counts.

## Emergency rollback

Prefer changing image tags in Git and allowing Flux to reconcile.

For temporary diagnosis:

```bash
kubectl rollout history deployment/<name> -n casinoshiz
kubectl rollout undo deployment/<name> -n casinoshiz
```

Commit the intended rollback to Git immediately afterward.
